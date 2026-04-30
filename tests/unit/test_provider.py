import copy

from ..base import make_provider


def test_set_model_failure_with_invalid_model(provider_manager):
    provider = make_provider(provider_manager)
    capabilities = copy.deepcopy(provider.capabilities)
    capabilities["validate_models"] = True
    provider.capabilities = capabilities
    success, response, user_message = provider.set_model("missing-model")
    assert success is False
    assert response is None
    assert "missing-model" in user_message
    assert "provider_fake_llm" in user_message
    assert "/plugin reload provider_fake_llm" in user_message
