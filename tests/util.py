def make_provider(provider_manager, provider_name='provider_fake_llm'):
    success, provider, user_message = provider_manager.load_provider(provider_name)
    if not success:
        raise Exception(user_message)
    provider.setup()
    return provider
