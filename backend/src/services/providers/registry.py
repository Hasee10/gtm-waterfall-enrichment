"""Maps WaterfallConfig.provider_name strings to provider client instances.

This is the one place that has to know every provider that exists. The
waterfall service only ever asks the registry for a client by name — it never
imports a provider class directly — so adding a new provider is: write the
client, register it here, add a WaterfallConfig row.
"""

from .apollo import ApolloClient
from .base import BaseProvider
from .hunter import HunterClient

PROVIDER_REGISTRY: dict[str, BaseProvider] = {
    "hunter": HunterClient(),
    "apollo": ApolloClient(),
}


def get_provider(provider_name: str) -> BaseProvider:
    """Look up a provider client by the name stored in WaterfallConfig."""
    try:
        return PROVIDER_REGISTRY[provider_name]
    except KeyError:
        raise ValueError(f"Unknown enrichment provider: {provider_name!r}") from None
