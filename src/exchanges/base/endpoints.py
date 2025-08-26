from abc import ABC
from typing import Dict, Literal, List

class Endpoint:
    """
    A class representing an API endpoint.

    Attributes
    ----------
    url : str
        The URL of the endpoint.

    method : str
        The HTTP method for the endpoint (GET, PUT, POST, DELETE).
    """

    def __init__(
        self, name: str, url: str, method: Literal["GET", "PUT", "POST", "DELETE", "NONE"]
    ) -> None:
        # NONE is a placeholder for base url's, which dont use a method.
        if method not in ["GET", "PUT", "POST", "DELETE", "NONE"]:
            raise ValueError(f"Invalid method for {url}: {method}")

        self.url = url
        self.method = method
        self.name = name

    def __repr__(self):
        return f"Endpoint(name='{self.name}, 'url='{self.url}', method='{self.method}')"

class Endpoints(ABC):
    """
    An abstract base class for managing API endpoints.

    Attributes
    ----------
    _endpoints_ : dict
        A dictionary to store the endpoint objects.
    """

    def __init__(self) -> None:
        self._endpoints_: Dict[str, Endpoint] = {}

    def add_endpoint(self, name: str, endpoint: Endpoint) -> None:
        """
        Add an endpoint to the endpoints dictionary.

        Parameters
        ----------
        name : str
            The name of the endpoint.

        endpoint : Endpoint
            The respective endpoint object.
        """
        self._endpoints_[name] = endpoint

    def load_endpoints(self, endpoints: List[Endpoint]) -> None:

        for endpoint in endpoints:
            self.add_endpoint(endpoint.name, endpoint)

    def __getattr__(self, name: str) -> Endpoint:
        """
        Get an endpoint by name.

        Parameters
        ----------
        name : str
            The name of the endpoint.

        Returns
        -------
        Endpoint
            The endpoint object.

        Raises
        ------
        AttributeError
            If the endpoint name does not exist in the endpoints dictionary.
        """
        try:
            return self._endpoints_[name]
        except KeyError:
            raise AttributeError(f"'Endpoints' object has no attribute '{name}'")
