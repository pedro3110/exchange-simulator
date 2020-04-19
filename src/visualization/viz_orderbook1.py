import numpy as np
import matplotlib.path as path
import matplotlib.animation as animation
import matplotlib.collections as mpl_collections
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt


class VizOrderbook1:

    def get_n_and_bins(self, data, n, min_price, max_price):
        if len(data) > 0:
            assert (max_price >= max(data))
        data_modified = [min_price] + data + [max_price]
        intervals = np.histogram_bin_edges(data_modified, n)
        a, b = np.histogram(data_modified, n)
        return a, b, intervals

    def get_verts_codes(self, data_all, n_bins, min_price, max_price):
        n, bins, _ = self.get_n_and_bins(data_all, n_bins, min_price, max_price)
        left = np.array(bins[:-1])
        right = np.array(bins[1:])
        bottom = np.zeros(len(left))
        top = bottom + n
        nrects = len(left)
        nverts = nrects * (1 + 3 + 1)
        verts = np.zeros((nverts, 2))
        codes = np.ones(nverts, int) * path.Path.LINETO
        codes[0::5] = path.Path.MOVETO
        codes[4::5] = path.Path.CLOSEPOLY
        verts[0::5, 0] = left
        verts[0::5, 1] = bottom
        verts[1::5, 0] = left
        verts[1::5, 1] = top
        verts[2::5, 0] = right
        verts[2::5, 1] = top
        verts[3::5, 0] = right
        verts[3::5, 1] = bottom
        return verts, codes, left, right, bottom, top

    def process(self, history, specific_steps=None, n_bins=10,
                max_size=50, frame_velocity=150, min_price=0, max_price=100):

        # Check input
        # Check
        #     ks1 = [x[0] for x in history['spreads']]
        #     ks2 = [x[0] for x in history['limit_orders']]
        #     ks3 = [x[0] for x in history['stop_orders']]
        #     ks4 = [x[0] for x in history['hidden_orders']]
        #     assert(ks1==ks2)

        fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(30, 10))
        plot_orders = {
            0: history['limit_orders'],
            1: history['stop_orders'],
            2: history['hidden_orders']
        }
        spreads = history['spreads']
        type_orders = {
            0: 'LIMIT', 1: 'STOP', 2: 'HIDDEN'
        }
        plot_animate = {i: {'history': None} for i in plot_orders}
        verts_base = None

        # Analyze
        for plot_id in plot_orders:
            orders = plot_orders[plot_id]

            # Get data
            map_step_time_tmp = {i: str(x[0]) for i, x in enumerate(orders)}
            if specific_steps is None:
                specific_steps = [i for i, _ in enumerate(map_step_time_tmp.items())]
            map_step_time_tmp = {
                k: v for k, v in map_step_time_tmp.items()
                if k in specific_steps}
            plot_animate[plot_id]['map_step_time'] = map_step_time_tmp
            orders = [order for i, order in enumerate(orders) if i in specific_steps]
            plot_animate[plot_id]['spreads'] = {str(k): v for k, v in spreads}

            # Orders
            orders = {str(k): v for k, v in orders}
            plot_animate[plot_id]['history'] = {}
            min_timestamp = float('inf')
            for timestamp in orders:
                min_timestamp = min(float(timestamp), min_timestamp)
                plot_animate[plot_id]['history'][timestamp] = {'bid': [], 'ask': [], 'all': []}
                for x in orders[timestamp]:
                    plot_animate[plot_id]['history'][timestamp]['all'].append(x[1])
                    if x[0] == 'Buy':
                        plot_animate[plot_id]['history'][timestamp]['bid'].append(x[1])
                    elif x[0] == 'Sell':
                        plot_animate[plot_id]['history'][timestamp]['ask'].append(x[1])
                    else:
                        raise Exception()
            # Generate limit bars index
            plot_animate[plot_id]['colors'] = {}
            for timestamp in orders:
                prices = plot_animate[plot_id]['history'][timestamp]['all']
                bids = plot_animate[plot_id]['history'][timestamp]['bid']
                asks = plot_animate[plot_id]['history'][timestamp]['ask']
                n, bins, intervals = self.get_n_and_bins(prices, n_bins, min_price, max_price)

                n_green, n_red = 0, 0
                max_bid = max(bids) if len(bids) > 0 else None
                min_ask = min(asks) if len(asks) > 0 else None
                if max_bid is not None:
                    n_green = len([col for col in intervals if col < max_bid])
                if min_ask is not None:
                    n_red = len([col for col in intervals if col > min_ask])
                bars_colors = [mcolors.to_rgb('g')] * (n_green - 1) + [mcolors.to_rgb('r')] * n_red
                plot_animate[plot_id]['colors'][timestamp] = bars_colors

            # Get initial geometry
            if min_timestamp < float('inf'):
                initial_timestamp = str(min_timestamp)
                verts_base, codes, left, right, bottom, top = self.get_verts_codes(
                    plot_animate[plot_id]['history'][initial_timestamp]['all'], n_bins, min_price, max_price)
                plot_animate[plot_id]['bars_shape'] = {
                    'left': left, 'right': right, 'bottom': bottom
                }
            else:
                plot_animate[plot_id]['bars_shape'] = None

        def animate(i):
            for plot_id in plot_orders:
                if plot_animate[plot_id]['bars_shape'] is not None:
                    # Get data actual
                    timestamp = plot_animate[plot_id]['map_step_time'][i]
                    prices = plot_animate[plot_id]['history'][timestamp]['all']
                    bars_color = plot_animate[plot_id]['colors'][timestamp]
                    bars_shape = plot_animate[plot_id]['bars_shape']

                    # Get top of bars
                    n, bins, _ = self.get_n_and_bins(prices, n_bins, min_price, max_price)
                    top_actual = bars_shape['bottom'] + n
                    verts_base[1::5, 1] = top
                    verts_base[2::5, 1] = top

                    # Set shape of figure
                    shape = np.array([[bars_shape['left'], bars_shape['left'], bars_shape['right'], bars_shape['right']],
                                     [bars_shape['bottom'], top_actual, top_actual, bars_shape['bottom']]]).T

                    pc = mpl_collections.PolyCollection(shape, facecolors=bars_color, alpha=0.7)
                    ax[plot_id].collections = []
                    ax[plot_id].add_collection(pc)

                    ax[plot_id].set_title('%s ==> (t=%s) (step=%i)' % (type_orders[plot_id], timestamp, i))
                    ax[plot_id].set_xlim(left[0], right[-1])
                    ax[plot_id].set_ylim(bottom.min(), max_size)
            # Ret animate
            return []

        # Ret process
        ani = animation.FuncAnimation(fig, animate, specific_steps,
                                      repeat=False, blit=True,
                                      interval=frame_velocity)
        return ani, animate
