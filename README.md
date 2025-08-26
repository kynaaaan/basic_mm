# Cryptocurrency Market Making

An asynchronous market making bot designed for cryptocurrency exchanges. This system implements order management, risk controls, and market data processing.

## Core Components

### **MarketMaker** (`src/market_maker.py`)
The main strategy engine that coordinates all components:
- Processes market data, position, and order events
- Triggers requoting based on configurable thresholds

### **OMS (Order Management System)** (`src/OMS.py`)
Handles all order lifecycle management:
- Routes orders to appropriate actions (place/amend/cancel)
- Tracks order states and prevents race conditions
- Implements order matching logic with client IDs

### **Quoting Engine** (`src/quoting_engines/simple.py`)
Generates competitive quotes using:
- **Volatility-based spreads**: Wider spreads in volatile markets
- **Geometric sizing**: Larger orders closer to mid-price
- **Position skewing**: Bias quotes away from inventory risk

### **Event Bus** (`src/core/event_bus.py`)
Manages asynchronous communication:
- Multi-symbol event routing


*This is a sanitized version showcasing technical architecture and implementation patterns. The actual trading logic and exchange integrations have been abstracted for demonstration purposes.*
