from enum import Enum
from abc import ABC
from typing import Dict

class Side(Enum):
    SELL = 0
    BUY = 1

class OrderType(Enum):
    MARKET = 0
    LIMIT = 1

class TIF(Enum):
    GTC = 0
    FOK = 1
    POST = 2

class StrNumConverter:
    """
    A base class for converting between numerical values and their string representations.

    This class provides methods to convert a numerical value to its string representation
    and vice versa. If the value or name is not found, it returns default unknown values.
    """

    DEFAULT_UNKNOWN_STR = "UNKNOWN"
    DEFAULT_UNKNOWN_NUM = -1.0

    def __init__(self, str_to_num: Dict[str, float]) -> None:
        self.str_to_num: Dict[str, float] = str_to_num
        self.num_to_str: Dict[float, str] = {v: k for k, v in self.str_to_num.items()}

    def to_str(self, value: float):
        """
        Converts a numerical value to its str representation.

        Parameters
        ----------
        value : float
            The numerical value to convert.

        Returns
        -------
        str
            The str representation of the numerical value.
            If the value is not found, returns "UNKNOWN".
        """
        return self.num_to_str.get(value, self.DEFAULT_UNKNOWN_STR)

    def to_num(self, name: str):
        """
        Converts a str name to its numerical representation.

        Parameters
        ----------
        name : str
            The str name to convert.

        Returns
        -------
        float
            The numerical representation of the str name.
            If the name is not found, returns -1.0.
        """
        return self.str_to_num.get(name, self.DEFAULT_UNKNOWN_NUM)

class SideConverter(StrNumConverter):
    """
    A converter class for trade sides, converting between string and numerical representations.

    Attributes
    ----------
    str_to_num : Dict
        A dictionary mapping string representations to numerical values.

    num_to_str : Dict
        A dictionary mapping numerical values to string representations.

    Parameters
    ----------
    BUY : str
        The string representation for the "buy" side.
    
    SELL : str
        The string representation for the "sell" side.
    """

    def __init__(self, BUY: str, SELL: str) -> None:
        super().__init__(str_to_num={f"{BUY}": Side.BUY, f"{SELL}": Side.SELL})

class OrderTypeConverter(StrNumConverter):
    """
    A converter class for order types, converting between string and numerical representations.

    Attributes
    ----------
    str_to_num : Dict
        A dictionary mapping string representations to numerical values.

    num_to_str : Dict
        A dictionary mapping numerical values to string representations.

    Parameters
    ----------
    LIMIT : str
        The string representation for the "limit" order type.

    MARKET : str
        The string representation for the "market" order type.

    STOP_LIMIT : str, optional
        The string representation for the "stop limit" order type. Default is None.

    TAKE_PROFIT_LIMIT : str, optional
        The string representation for the "take profit limit" order type. Default is None.
    """

    def __init__(
        self,
        LIMIT: str,
        MARKET: str,
    ) -> None:
        super().__init__(
            str_to_num={
                f"{LIMIT}": OrderType.LIMIT,
                f"{MARKET}": OrderType.MARKET,
            }
        )

class TimeInForceConverter(StrNumConverter):
    """
    A converter class for time-in-force policies, converting between string and numerical representations.

    Attributes
    ----------
    str_to_num : Dict
        A dictionary mapping string representations to numerical values.

    num_to_str : Dict
        A dictionary mapping numerical values to string representations.

    Parameters
    ----------
    GTC : str
        The string representation for "good till canceled".

    FOK : str
        The string representation for "fill or kill".

    POST_ONLY : str
        The string representation for "post only".
    """

    def __init__(self, GTC: str, FOK: str, POST: str) -> None:
        super().__init__(
            str_to_num={
                f"{GTC}": TIF.GTC,
                f"{FOK}": TIF.FOK,
                f"{POST}": TIF.POST,
            }
        )

class SymbolConverter:
    """ 
    A class for converting between exchange symbols and internal representations.
    """

    def __init__(self, exch_rep: str):
        self.exch_rep = exch_rep
        

    def to_norm(self, symbol: str) -> str:
        """
        Converts an exchange symbol to its normalized form.

        Parameters
        ----------
        symbol : str
            The exchange symbol to convert.

        Returns
        -------
        str
            The normalized symbol.
        """
        pass

    def to_exch(self, symbol: str) -> str:
        """
        Converts a normalized symbol to its exchange representation.

        Parameters
        ----------
        symbol : str
            The normalized symbol to convert.

        Returns
        -------
        str
            The exchange representation of the symbol.
        """
        return symbol + self.exch_rep
        