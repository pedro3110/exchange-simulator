Usability
1. make an initial refactoring. Standarize behavior of agents (inside vs. outside of exchange)
2. standarize the protocol to create a new trading agent
 


Visualizations
1. line plot: evolution of bid vs. ask
2. line plot: evolution of bid/ask spread
3. animated histogram: evolution in time of orderbook data structure (limit, stop, market queues)


Trading agents
1. reproducibility: log all orders sent
2. increase realism: limit trading time
3. increase realism: format time as '11:00:00' instead of using float's
4. increase realism: agents have limited cash and limited number of each contract
5. calculate returns of each agent at any given time
6. new agent: Broker. Has to fulfill a list of trades before the session ends. He will profit depending on when he program the operation
7. new agent: schedule cancellations of orders in certain market conditions
8. new agent: replay agent based on lobster data. Verify that price moves correctly
9. Reinforcement agent that receives periodic updates on the price of a security (external, macro information) 
and according to this can act in a market, buying (or selling, or both) securities in it
10. ZI (Zero Intelligence) agents and intelligent (for example trained with Direct Reinforcement Learning) agents 
interact in a market. The intelligent one should have more returns
11. new agent: have a portfolio. Rebalancing strategies.
12. new agent: Market makers. detect uninformed traders / informed traders


Limit order book:
1. more flexibility: allow iceberg orders
2. orders: carefully log the transformation of market orders into limit orders, or stop orders into market or limit orders
3. Optimization: implement new LOB, limiting levels and min/max price (with hash tables)
4. orders: hidden orders
5. orders: calculate bid (ask) side depth available at price p := f(p, t)
6. implement different sampling methods for the snapshots (time series have very != behavior depending on this)
7. new feature: allow to split and modify orders

Exchange
1. increase realism: check that every order entering into the exchange arrives before the end time of the session
2. new feature: calculate transaction costs of each exchange for each agent
3. Allow the market to halt (agents send orders but regulator doestn't send it to Orderbook). This way agents can 
observe evolution of external signal while the market stabilizes
4. new feature: add intermediary between agents and exchange. The messages are not broadcasted but send specifically to the right agent
5. establish protocol to set order's id's (now, they are all random and an an exception is raised if an LOB tries has a duplicate id)


Analysis
1. measure orders effect on liquidity: trading time, tightness, depth, resiliency
2. measure market impact signals: VPIN, Price Impact, Window spread indicator, OBWA spread, Manual spread
3. Program different stochastic evolution of price (brownian motion vs. special function with noise)
4. Program specific trading strategies. For example, supervielle strategy
5. Replicate ABIDES paper
6. nowcasting. VPIN metrics
7. coordination between some agents. How can we generate 'hombro-cabeza-hombro' in an emergent way?
8. Analyze effects of: market impact, transaction costs, taxes
9. Analyze strategies: profit, wealth, utility function of wealth, performance ratios (eg. sharpe)
10. emergent behaviour of agents: generate high market volatility vs. low volatility
11. Liquidation strategies. Evaluate algorithms in different environments
12. Study slippage: when agents get a price != than desired because the order executes at a different time than created
13. Emergent behavior in LOBs. Replicate regularities of different markets


Financial engineering & Machine Learning
1. Theory implied correlation matrix TICs
2. Knowledge graphs: topological representation of covariance matrix (richer rep)
    * multicollinearity in financial system (condition number, determinant of matrix)
    * high mutual information. Clusters of highly codependent variables
3. Backtesting:
    * Historical scenarios (walk forward)
    * Combinatorial cross validation (resampling from obervations)
    * Montecarlo data generating process (bootstrap investment strategies). Fit regime switch MCMC, GUM, VAEs
4. 