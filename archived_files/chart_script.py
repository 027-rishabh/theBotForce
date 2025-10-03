# Create a flowchart for DEX/CEX arbitrage trading bot strategy
diagram_code = """
flowchart TD
    A[Monitor Prices] --> B[Calc Difference]
    B --> C{Within 2% Range?}
    C -->|Yes| D[Place Orders<br/>DEX±1%]
    C -->|No| A
    D --> E[Monitor Movement]
    E --> F{Price Moved 2%?}
    F -->|No| E
    F -->|Yes| G[Wait 2 Minutes]
    G --> H[Cancel Orders]
    H --> I[Rebalance]
    I --> E
"""

# Create the mermaid diagram and save as both PNG and SVG
create_mermaid_diagram(diagram_code, 'arbitrage_flowchart.png', 'arbitrage_flowchart.svg')