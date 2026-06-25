#let user choose from provided llm services (custom llm provider for later stages)
PROVIDER_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}

PROVIDER_MODELS = {
    "groq": "llama-3.1-8b-instant",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash-lite",
}

#mdoule level llm config dict
llm_config = {
    "provider": None,
    "api_key": None,
    "base_url": None,
    "model": None,
}

def configure_llm(provider, api_key):
    provider = provider.strip().lower()
    
    if provider not in PROVIDER_URLS:
        raise ValueError(f"provider '{provider}' not supported or there is a typing error. supported: {', '.join(PROVIDER_URLS.keys())}")
    
    llm_config["provider"] = provider
    llm_config["api_key"] = api_key
    llm_config["base_url"] = PROVIDER_URLS[provider]
    llm_config["model"] = PROVIDER_MODELS[provider]