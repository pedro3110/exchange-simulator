from datetime import datetime, timedelta
import math
import pandas as pd
from enum import Enum


class Indicator:
    pass


class Strategy:
    pass


class BackgroundScheduler:
    def add_job(self, scheduled_function, trigger, args):
        pass

    def start(self):
        pass


class DateTrigger:
    def __init__(self, run_date):
        self.run_date = run_date


class Position:
    def __init__(self):
        self.size = 0


class Order(Enum):
    Buy = 0
    Sell = 1
    Cancelled = 2
    Canceled = 3
    Limit = 4


class NewOrder:
    def __init__(self):
        self.m_orderId = 0
        self.price = 0
        self.abs_size = 0


"""
Required libraries (TODO: simulate)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from arquants import Strategy, Order

Ciclo de vida
1. __init__
2. start
3. prenext: este metodo es llamado hasta que el periodo minimo (declarado en __init__) se cumpla
3.1 nextstart se llama una unica vez, cuando comienza a ejecutarse next
4. next
5. stop

Pregunta: y el metodo notify_trade? No esta implementado. Cual es la diferencia con notify_order? (diferencia entre trade y order)
Pregunta: que es una instancia de linea?
Pregunta: cual es la diferencia entre una orden Partial y una Accepted?

Notas:
1. self.datas[0] == self.data0 == self.agents_data
2. Tipos de orden: Orden.{Limit, Stop, StopLimit, Market}
3. Limites de orden: valid == {None: GTC (Good till cancelled), datetime: GTD (Good till date, valida hasta cierta fecha/horario),
   Order.DAY o timedelta(): hasta el fin de la sesion }
Estados: Created, Submitted, Accepted, Partial, Complete, Rejected, Canceled, Expired.
4. setsizer vs. getsizer: cada Estrategia tiene un Sizer, que determina la cantidad def contratos que compra/vende la estrategia
 ver metodo _getsizing(self, comminfo, cash, agents_data, isbuy)
5. antes de cada llamado a next se precalcula los indicadores declarados en __init__
6. Esta bueno que la logica declarada en next quede bien sencilla, y haga uso de variables/condiciones definidas en __init__
"""


class SUPVAbsorbeTasa(Strategy):
    """
    agents_data = [bid_px,bid_qty,last_px,last_qty,offer_px,offer_qty,open,high,low,close,volume,open_interest]

    Idea de la estrategia:
    determino si la tasa que pago por ser tomador de pesos vendiendo en CI y comprando en 48hs es < que la tasa que gano por otro lado, es decir,
    por la tasa que gano prestando pesos en 48hs. Al ser un banco, tengo suficiente volumen para hacer dar estos prestamos de corto plazo. Además,
    las comisiones que pagan son muy bajas comparado con otros agentes del mercado (derechos = 0.01% vs 0.5% que se les cobra a personas fisicas)
    # TODOs:
    # 1. TTL aplicarlo a la orden agresora y cancelarlo
    # 2. nominales es size y no volumen
    # 3. el aforo esta expresado en terminos de porcentaje sobre la cantidad -- debería ser 1=100%
    """
    columns = ['px_ci', 'qty_ci', 'px_48', 'qty_48', 'changed']


    def __init__(self,
                 max_tasa=1, volumen=1000, derechos=0.0001, ttl=1,
                 hora_fin='15:55:00', dias=2, lote_max=100, aforo=0.1,
                 tick_a_mejorar=0.03, max_descalce=100):

        self.max_tasa = max_tasa
        self.volumen = volumen
        self.derechos = derechos
        self.ttl = ttl
        self.hora_fin = hora_fin
        self.dias = dias
        self.lote_max = lote_max
        self.aforo = aforo
        self.tick_a_mejorar = tick_a_mejorar
        self.max_descalce = max_descalce

        self.scheduler = BackgroundScheduler()

        self.sell_volume = 0
        self.buy_volume = 0

        self.df = pd.DataFrame(columns=self.columns)

        self.to_send_order = list()
        self.cancel_now = list()

        self.pending_new_orders = dict()
        self.current_passive_order = None
        self.pending_cancel_orders = dict()

        self.check_on_new = False

        self.sell_orders = dict()

        self.order_to_shot = dict()

        self.size_executed = dict()
        self.to_replace = dict()

        self.init_df()
        self.init_scheduler()

        #########################
        # Atributos pre-definidos
        self.data0 = None
        self.data1 = None

    #########################
    # Metodos pre-definidos
    def pause(self):
        pass

    def cancel(self, order):
        pass

    def buy(self, *args, **kwargs):
        return NewOrder()

    def sell(self, *args, **kwargs):
        return NewOrder()

    def log(self, msg):
        pass

    def sendOrders(self, ls):
        pass

    def getposition(self, data):
        return Position()


    '''
    Mediante este metodo se determina el envio de nuevas ordenes (buy/sell/cancel), de acuerdo al mercado y al estado de la estrategia.
    Este es el paso 1 correspondiente a la ejecucion de cada orden (en notify_order vamos a recibir la respuesta del mercado sobre el status de c/ orden)
    '''

    def next(self):
        # Obtener info asociada a los contratos de interes
        self.load_md()

        # Procesamiento del nuevo update (esto se hace previo a la ejecucion de 'next').
        # Aca se programa el envio de nuevas ordenes en (to_send_order, order_to_shot)
        self.process_df()

        # Protocolo de cancelacion de ordens: revisa las ordenes en cancel_now y si corresponde las envia a ser canceladas
        self.process_cancel_now()

        if self.descalce_valido():

            # En process_df se determinó previamente si se encolaban nuevas ordenes para ser enviadas
            if len(self.to_send_order) > 0:

                # Agarro la nueva orden (encolada para ser enviada)
                new_order = self.to_send_order[0]

                # Si no hay ordenes pendientes ...
                if len(self.pending_new_orders) == 0:
                    if self.current_passive_order is not None:
                        # No hay pending new orders pero current_passive_order es una orden (es una orden activa)
                        self.log("hay una orden de compra activa %s" % self.current_passive_order.m_orderId)

                        # Pregunta: por que podria ser la misma orden self.to_send_order[0] vs. self.current_passive_order (c/ ejec. parcial) ?
                        if len(self.pending_cancel_orders) == 0:
                            size_executed = self.size_executed.get(self.current_passive_order.m_orderId, 0)
                            if not self.same_order(new_order.price, new_order.abs_size,
                                                   self.current_passive_order.price,
                                                   self.current_passive_order.abs_size - size_executed):

                                # Envio orden de compra remanente (en to_send_order solo se encolan ordenes de compra) y cancelo la que habia quedado parcial
                                self.cancel(self.current_passive_order)
                                self.sendOrders([new_order])
                                self.pending_cancel_orders[
                                    self.current_passive_order.m_orderId] = self.current_passive_order
                                self.pending_new_orders[new_order.m_orderId] = new_order

                            else:
                                self.log("No se envia porque es la misma orden")
                        else:
                            self.log("Todavia hay pendiente de cancelacion")
                    else:
                        # No hay pending new orders y tampoco hay alguna current_passive_order
                        # current_passive_order is None. Envio la nueva orden y la marco como pending
                        self.sendOrders([new_order])
                        self.pending_new_orders[new_order.m_orderId] = new_order
                        self.log("envio la orden, y la pongo como pending new el id es %s" % new_order.m_orderId)
                else:
                    # Aun hay ordenes pendientes. Guardo la orden en estructura de datos to_replace
                    self.log(
                        "hay ordenes pendientes, no se envia la orden %s y se pone check on new en true" % new_order.m_orderId)
                    self.check_on_new = True
                    info = dict()
                    info['price'] = new_order.price
                    info['size'] = new_order.abs_size
                    info['order_to_shot'] = self.order_to_shot[new_order.m_orderId]
                    del self.order_to_shot[new_order.m_orderId]
                    for key in self.pending_new_orders.keys():
                        # Agrego todas las ordenes pending a to_replace
                        self.log("Pongo la orden %s en to_replace" % key)
                        self.to_replace[key] = info
                        break
            else:
                # No hay ordenes encoladas para ser enviadas
                self.log("send orders es 0")
        else:
            self.log("descalce invalido")
        self.to_send_order.clear()

    '''
    Mediante este metodo notifica cambios en una orden. Aca se regula que hacer con las ordenes que ya se enviaron
    '''

    def notify_order(self, order):
        if order.status == Order.Accepted:
            # ORDEN ACEPTADA. check_on_new me dice si tengo que chequear las pending orders updates / cancelaciones
            if order.m_orderId in self.pending_new_orders.keys():
                self.log("la orden aceptada esta pending new {}".format(order.m_orderId))
                if self.check_on_new:
                    self.log("check on new estaba true {}".format(order.m_orderId))
                    # La orden aceptada esta pending_new y check_on_new
                    # Chequear si hay que reemplazar esta orden. Las ordenes pendientes de aceptacion se procesan de a una
                    if order.m_orderId in self.to_replace.keys():
                        executed_size = self.size_executed.get(order.m_orderId, 0)
                        if executed_size != 0:
                            size = self.to_replace[order.m_orderId]['size'] + executed_size
                        else:
                            size = self.to_replace[order.m_orderId]['size']

                        price = self.to_replace[order.m_orderId]['price']
                        if not self.same_order(price, size, order.price, order.abs_size - executed_size):
                            # Cancelo la orden original
                            self.cancel(order)

                            # Creacion de nueva orden a partir de la que habia en to_replace. Por default, exectype = Market y size = 1
                            # La orden es creada con el size que corresponda
                            new_order = self.buy(data=order.data, price=price, size=size, exectype=Order.Limit)
                            # Seteo la orden_to_shot correspondiente a new_order (tiene que ser la misma que correpondia a la orden original)
                            self.order_to_shot[new_order.m_orderId] = self.to_replace[order.m_orderId]['order_to_shot']

                            self.log("reemplazando orden vieja: %s nueva: %s" % (order.m_orderId, new_order.m_orderId))

                            # Agrego la orden cancelada y la nueva a estructuras de datos para trackear su ejecución
                            # La orden original fue PARCIALMENTE completada. Cancelo la anterior y envio una nueva con size = 'lo que no se ejecuto'
                            self.pending_cancel_orders[order.m_orderId] = order
                            self.pending_new_orders[new_order.m_orderId] = new_order
                        # Fijo esta orden como la activa corriente (orden Accepted BUY)
                        # Si era necesario ya la reemplacé. Entonces, quito esa orden de pending y de to_replace y ahora es la current passive
                        # Trackeo self.current_passive_order para poder cancelarla eventualmente
                        self.current_passive_order = order
                        del self.pending_new_orders[order.m_orderId]
                        del self.to_replace[order.m_orderId]
                    else:
                        # Nueva orden activa (orden Accepted BUY)
                        # Trackeo self.current_passive_order para poder cancelarla eventualmente
                        self.current_passive_order = order
                        self.cancel(order)
                        del self.pending_new_orders[order.m_orderId]
                        self.pending_cancel_orders[order.m_orderId] = order
                    self.check_on_new = False
                else:
                    # La orden activa pasa a ser esta (que fue aceptada, orden Accepted BUY).
                    # Esta orden ya no esta pending (porque acaban de avisar que esta Accepted)
                    # Trackeo self.current_passive_order para poder cancelarla eventualmente
                    self.log("current_passive_order se vuelve order ")
                    self.current_passive_order = order
                    if order.m_orderId in self.pending_new_orders.keys():
                        del self.pending_new_orders[order.m_orderId]

        elif order.status == Order.Partial:
            # ORDEN PARCIAL: la orden fue ejecutada solamente de forma parcial (< volumen total requerido)
            if order.ordtype == Order.Buy:
                self.log("una orden de compra se completo parcialmente")
                size = self.register_size_executed(order)

                # Sell order correspondiente a esta Buy Order que esta completada parcialmente
                sell_order = None
                if order.m_orderId in self.order_to_shot.keys():
                    sell_order = self.order_to_shot[order.m_orderId]
                else:
                    self.log("No se encontró la orden de venta a enviar")
                    return

                # Se encontro la orden de venta a enviar en order_to_shot.
                # Envio orden de venta pero para size = (la cantidad de contratos que se ejecutaron de la orden de compra correspondiente)
                # Al mismo tiempo scheduleo su cancelacion (si transcurre cierto tiempo determinado por self.ttl)
                sell_order = self.sell(data=self.data0, price=sell_order.price, size=size, exectype=Order.Limit, send=False)

                # Schedule orden de venta (desde notify_order)
                self.log("envio orden de venta")
                self.sell_orders[sell_order.m_orderId] = sell_order
                self.sendOrders([sell_order])
                self.schedule_cancel(sell_order.m_orderId)

                # Orden activa (orden Partial BUY): la saco de pending pero la dejo en current_passive_order
                # Trackeo self.current_passive_order para poder cancelarla eventualmente
                self.current_passive_order = order
                if order.m_orderId in self.pending_new_orders.keys():
                    del self.pending_new_orders[order.m_orderId]
                self.buy_volume += size
                self.log("Volumen comprado en 48: %s" % self.buy_volume)

            elif order.ordtype == Order.Sell:
                self.log("se opero parcialmente una orden de venta %s" % order.m_orderId)
                size = self.register_size_executed(order)
                self.sell_volume += size
                self.log("Volumen vendido en CI: %s" % self.sell_volume)

        elif order.status == Order.Completed:
            if order.ordtype == Order.Buy:
                # Se concreta una orden de compra completa
                self.log("Se lleno una orden de compra")
                size = self.register_size_executed(order)
                sell_order = None
                if order.m_orderId in self.order_to_shot.keys():
                    sell_order = self.order_to_shot[order.m_orderId]
                else:
                    self.log("No se encontró la orden de venta a enviar")
                    return
                if size != sell_order.abs_size:
                    # Actualizo la orden de venta si el size es distinto al ejecutado por la orden compra ya ejecutada
                    sell_order = self.sell(data=self.data0, price=sell_order.price, size=size, exectype=Order.Limit, send=False)
                self.buy_volume += size

                # Schedule orden de venta (desde notify_order)
                self.log("enviando orden de venta")
                self.sendOrders([sell_order])
                self.schedule_cancel(sell_order.m_orderId)
                self.sell_orders[sell_order.m_orderId] = sell_order

                # Desactivo current order activa de forma completa (siempre es una orden de BUY)
                self.current_passive_order = None
                if order.m_orderId in self.pending_new_orders.keys():
                    del self.pending_new_orders[order.m_orderId]
                if order.m_orderId in self.pending_cancel_orders.keys():
                    del self.pending_cancel_orders[order.m_orderId]
                if order.m_orderId in self.order_to_shot.keys():
                    del self.order_to_shot[order.m_orderId]
                if order.m_orderId in self.size_executed.keys():
                    del self.size_executed[order.m_orderId]
                self.log("Volumen comprado en 48: %s" % self.buy_volume)

            elif order.ordtype == Order.Sell:
                # Se concreta una orden completa (buy_48 + sell_ci)
                self.log("Se lleno una orden de venta id %s" % order.m_orderId)
                size = self.register_size_executed(order)
                self.sell_volume += size
                if order.m_orderId in self.sell_orders.keys():
                    del self.sell_orders[order.m_orderId]
                if order.m_orderId in self.size_executed.keys():
                    del self.size_executed[order.m_orderId]
                self.log("Volumen vendido en CI: %s" % self.sell_volume)

        elif order.status in (Order.Cancelled, Order.Canceled):
            if order.m_orderId in self.pending_cancel_orders.keys() or (self.current_passive_order is not None and
                                                                                self.current_passive_order.m_orderId == order.m_orderId):
                if order.m_orderId in self.pending_cancel_orders.keys():
                    del self.pending_cancel_orders[order.m_orderId]
                if self.current_passive_order is not None and self.current_passive_order.m_orderId == order.m_orderId:
                    # Desactivo current order activa (siempre es una orden de BUY)
                    self.current_passive_order = None
                if order.m_orderId in self.order_to_shot.keys():
                    del self.order_to_shot[order.m_orderId]
                if order.m_orderId in self.size_executed.keys():
                    del self.size_executed[order.m_orderId]
            elif order.m_orderId in self.sell_orders.keys():
                del self.sell_orders[order.m_orderId]
                if order.m_orderId in self.pending_cancel_orders.keys():
                    del self.pending_cancel_orders[order.m_orderId]

        elif order.status == Order.Rejected:
            if order.m_orderId in self.pending_new_orders.keys():
                del self.pending_new_orders[order.m_orderId]
            if order.m_orderId in self.to_replace.keys():
                del self.to_replace[order.m_orderId]
            if order.m_orderId in self.sell_orders.keys():
                del self.sell_orders[order.m_orderId]
            if order.m_orderId in self.pending_cancel_orders.keys():
                del self.pending_cancel_orders[order.m_orderId]
        else:
            # Habria que loguear que esta orden esta siendo notificada pero no entra en ningun caso
            pass

    def on_pause(self):
        self.log("Se  apreto pausa. Quitando las ordenes activas")
        if self.current_passive_order is not None:
            self.cancel(self.current_passive_order)
        for order in self.sell_orders.values():
            self.cancel(order)
        if len(self.pending_new_orders) > 0:
            self.check_on_new = True

    def on_error(self):
        self.log("Ha habido un error")
        self.on_pause()

    '''
    Este metodo procesa las ordenes que deberian ser canceladas.
    '''

    def process_cancel_now(self):
        for order in self.cancel_now:
            # la orden debe ser cancelada
            # busco la orden si no esta pending pero ya fue aceptada (current_passive_order)
            if order.m_orderId not in self.pending_new_orders.keys():
                if self.current_passive_order is not None and self.current_passive_order.m_orderId == order.m_orderId:
                    if order.m_orderId not in self.pending_cancel_orders.keys():
                        self.cancel(order)
                        self.pending_cancel_orders[order.m_orderId] = order
                    else:
                        self.log("Ya en se envio a cancelar la orden %s" % order.m_orderId)
            else:
                # la orden deberia ser cancelada y ya fue enviada, pero aun no esta confirmada (esta en pending_new_orders)
                self.log("la orden esta pendiente de confirmacion %s" % order.m_orderId)
                self.check_on_new = True

    def descalce_valido(self):
        # Pregunta: self.position == self.getposition({contrato})
        self.log(
            "decalse: comprado %s - vendido %s - maximos %s" % (abs(self.getposition(self.data0).size),
                                                                abs(self.getposition(self.data1).size),
                                                                self.max_descalce))
        return abs(abs(self.getposition(self.data0).size) - abs(self.getposition(self.data1).size)) < self.max_descalce
        # return abs(self.buy_volume - self.sell_volume) < self.max_descalce
        # Ambos returns deberian dar lo mismo, no? (por seguridad / posibles bugs por intertemporalidad, se usa el metodo de Strategy directamente?)

    def register_size_executed(self, order):
        size_executed = self.size_executed.get(order.m_orderId, 0)
        current_trade = abs(order.executed.size) - size_executed
        self.size_executed[order.m_orderId] = abs(order.executed.size)
        return current_trade

    def same_order(self, price, size, old_px, old_size):
        self.log("Chequeando si la orden es igual. Nueva px-qty: %s - %s. Vieja px-qty: %s - %s" % (price, size, old_px, old_size))
        return price == old_px and size == old_size

    def process_df(self):
        # Agarra el update (primera fila deberia ser) y lo procesa
        temp = self.df.query('changed==True')
        temp.apply(self.process, axis=1)

    '''
    Procesamiento de un nuevo update del estado del Order Book
    '''

    def process(self, row):

        # BUSCAR ORDEN DE COMPRA (para revisar si hay que hacer cambios)
        buy_order = self.current_passive_order
        if buy_order is None:
            pending_list = list(self.pending_new_orders.values())
            if len(pending_list) > 0:
                buy_order = pending_list[0]

        # Valido que el precio de la current_passive_order es >= el precio a 48hs? ()
        passive_valid = self.validate_buy_order(order=buy_order, px=row['px_48'])

        # BUSCAR ORDEN DE VENTA (para revisar si hay que hacer cambios)
        sell_order = False
        if buy_order is not None:
            # Hay orden de compra (no se sabe si valida) Y de venta (no se sabe si valida): passive_valid in {True, False} y sell_order in {True, False}
            self.log("validando activa")
            # Obtengo la orden de venta relacionada con la orden de compra activa corriente (currenet_passive_order)
            # Comparo el ultimo dato que tengo para este contrato con la orden de venta correspondiente en self.order_to_shot a esta orden de compra
            found_order = self.order_to_shot.get(buy_order.m_orderId, None)
            sell_order = self.validate_sell_order(order=found_order,
                                                  px=row['px_ci'],
                                                  qty=min(int(row['qty_ci'] * (1 - self.aforo)
                                                              if not math.isnan(row['qty_ci'])
                                                              else 0),
                                                          self.lote_max))
        else:
            self.log("no hay orden de compra por ende no hay orden de venta")
        self.log("pasive %s - active %s" % (passive_valid, sell_order))

        # Si la info nueva llega invalida, cancelo la orden y finalizo. Por que no lo hago mas arriba esto?
        if not self.valid_md(row):
            if buy_order is not None:
                self.cancel_now.append(buy_order)
            return

        # RECALCULAR LA TASA (si es necesario)
        # Si la orden de compra pasaron a ser invalidas (passive_valid) ó la orden de venta es invalida (sell_order), recalcular la tasa y actualizar ordenes
        if not (passive_valid and sell_order):
            self.log("recalculando tasa")
            vol_ci = int(row['qty_ci'] * (1 - self.aforo))
            vol = min(vol_ci, self.volumen - self.sell_volume)

            if vol > self.lote_max:
                vol = self.lote_max

            # Calculo el precio a pagar por contrato 48hs. := px_48hs + tick_a_mejorar (tick_a_mejorar == 0.03)
            next_price = self.get_next_price(buy_order)

            # Calculo de la tasa tomadora = f(price_48hs, price_00hs). self.dias == 2 (porque son 48hs ?)
            tasa = (((next_price) * (1 + self.derechos)) / (row['px_ci'] * (1 - self.derechos)) - 1) / self.dias * 365
            self.log("Tasa actual = %s" % tasa)

            if tasa <= self.max_tasa and vol > 0:
                self.log("Armando la orden")
                price_ci = row['px_ci']

                # PUNTO CLAVE 1. Inicializar ordenes de la estrategia: buy(48hs) + sell(ci)
                sell_ci = self.sell(data=self.data0, price=price_ci, size=vol, exectype=Order.Limit, send=False)
                buy_48 = self.buy(data=self.data1, price=next_price, size=vol, exectype=Order.Limit, send=False)

                # Encolamiento de una orden de compra en 48hs (P1) a to_send_order
                self.to_send_order.append(buy_48)
                # PUNTO CLAVE 2. Agrego una orden de venta (P2) en 00hs vs. la orden P1 a order_to_shot
                self.order_to_shot[buy_48.m_orderId] = sell_ci
            else:
                self.log("no da la tasa")
                if buy_order is not None:
                    self.log("Tasa actual: %s - Tasa maxima: %s - Se cancelará la orden" % (tasa, self.max_tasa))
                    self.cancel_now.append(buy_order)
        # Si ambas ordenes son validas, no hace falta recalcular ninguna tasa
        else:
            self.log("ambas ordenes siguen vigentes ")

    def valid_md(self, row):
        return not (math.isnan(row['px_ci']) or
                    math.isnan(row['qty_ci']) or
                    math.isnan(row['px_48']) or
                    math.isnan(row['qty_48']))

    def get_next_price(self, order):
        if order is not None and (
                        order.price == self.data1.bid_px[0] or order.price == self.data1.bid_px[
                    0] + self.tick_a_mejorar):
            return order.price
        if order is not None:
            self.log("son distintos %s %s" % (order.price, self.data1.bid_px[0]))
        else:
            self.log("order is none")
        return self.data1.bid_px[0] + self.tick_a_mejorar

    def validate_buy_order(self, order, px):
        self.log("validando vigencia orden de compra ")
        if order is None:
            self.log("no hay orden de compra")
            return False
        self.log("la orden de compra con stado %s tiene precio %s y el precio de mercado es %s" % (
        order.status, order.price, px))
        price_valid = order.price >= px
        return price_valid

    def validate_sell_order(self, order=None, px=None, qty=None):
        self.log("validando vigencia de orden de venta")
        if order is None:
            self.log("no hay orden de venta")
            return False
        self.log("orden de venta px %s - market px %s" % (order.price, px))
        price_valid = order.price == px
        self.log("orden de venta qty %s - market qty %s " % (order.abs_size, qty))
        qty_valid = order.abs_size == qty
        return price_valid and qty_valid

    def load_md(self):
        self.df['changed'] = False
        new_md = self.get_md()
        # Actualizacion de dataframe
        if not self.df.loc[0].equals(new_md):
            self.df.loc[0] = new_md
            # Setea changed = True en la primera fila del dataframe
            self.df.iat[0, 4] = True

    '''
    Metodo para obtener el market agents_data
    Data feed: los objetos [self.data0, self.data1, ...] contienen informacion para los contratos especificados en la sesión (BT Backtesting o LT Livetrading)
    bid_px, bid_qty
    last_px, last_qty, offer_px, offer_qty, open, high, low, close, volume, openinterest
    '''

    def get_md(self):
        to_return = dict()

        # ci = contado inmediat; 48 = plazo 48hs
        to_return['px_ci'] = float(format(self.data0.bid_px[0], '.3f'))
        to_return['qty_ci'] = float(format(self.data0.bid_qty[0], '.3f'))
        to_return['px_48'] = float(format(self.data1.bid_px[0], '.3f'))
        to_return['qty_48'] = float(format(self.data1.bid_qty[0], '.3f'))
        to_return['changed'] = False
        return pd.Series(to_return)

    def init_df(self):
        self.df.loc[0] = [0] * len(self.columns)

    def init_scheduler(self):
        now = datetime.now()
        date = now.strftime("%Y-%m-%d, " + self.hora_fin)
        run_date = datetime.strptime(date, "%Y-%m-%d, %H:%M:%S")
        run_date = run_date + timedelta(hours=3)
        trigger = DateTrigger(run_date=run_date)
        self.scheduler.add_job(self.scheduled_function, trigger=trigger)
        self.scheduler.start()

    def scheduled_function(self):
        self.pause()

    def schedule_cancel(self, order_id):
        scheduler = BackgroundScheduler()
        now = datetime.now()
        run_date = now + timedelta(seconds=self.ttl)
        trigger = DateTrigger(run_date=run_date)
        scheduler.add_job(self.cancel_order, trigger=trigger, args=[order_id])
        scheduler.start()

    def cancel_order(self, id):
        if id in self.sell_orders.keys():
            order = self.sell_orders[id]
            self.cancel(order)
            self.pending_cancel_orders[id] = order
