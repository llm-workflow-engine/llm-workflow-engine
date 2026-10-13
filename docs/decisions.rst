Decision models
===============

Decision models evaluate named questions against text or structured state and
return probabilities and typed answers. LWE exposes them through a Python API
and the ``lwe_decide`` Ansible module. They do not create chat conversations,
run tools, or appear in the interactive CLI's provider/model selections.

Install a provider
------------------

Install the provider packages you need from GitHub::

    pip install git+https://github.com/llm-workflow-engine/lwe-plugin-decision-cloudflare
    pip install git+https://github.com/llm-workflow-engine/lwe-plugin-decision-typesafe

See the `Cloudflare plugin <https://github.com/llm-workflow-engine/lwe-plugin-decision-cloudflare>`_
and `TypeSafe plugin <https://github.com/llm-workflow-engine/lwe-plugin-decision-typesafe>`_
for credentials, supported models, and provider-specific configuration.
Plugins register entry points in
``lwe_decision_providers`` and require no ``plugins.enabled`` setting.

Python usage
------------

.. code-block:: python

    from lwe.decisions import (
        Choice, DecisionRequest, DecisionService, DecisionSettings, Noul, Score,
    )

    service = DecisionService(DecisionSettings(
        provider="cloudflare",
        model="clef-omni",
        timeout=30.0,
        max_retries=2,
    ))
    request = DecisionRequest(
        state={"message": "Checkout is unavailable.", "customer_id": 42},
        questions={
            "urgent": Noul(instructions="Does this require urgent attention?"),
            "team": Choice(
                instructions="Which team should handle this?",
                criteria={"support": "Product problems", "billing": "Invoices", "other": "Other"},
            ),
            "severity": Score(
                instructions="How severe is the impact?",
                criteria=["No impact", "Minor", "Major", "Critical"],
            ),
        },
    )
    result = service.decide(request)
    data = result.model_dump(mode="json", exclude_none=True)
    print(data["answers"])

``DecisionRequest.model_validate(mapping)`` accepts ordinary JSON-compatible
request dictionaries. ``state`` is a string, object, or array, and remains
structured. Questions are ``noul``, ``choice``, or ``score`` objects. One request
accepts 1–64 questions with IDs containing letters, digits, underscores, dots,
and hyphens (up to 100 characters). A choice selects one label; multi-label
classification can be expressed as multiple ``noul`` questions.

The synchronous service is stateless with respect to conversations. It accepts
an optional provider instance for embedding or testing. Ordinary application
code can wrap ``service.decide`` in a LangChain ``RunnableLambda`` if composition
is useful; Runnable machinery is not required for direct Python usage.

Results and policy
------------------

Each result contains ``provider``, ``model``, ``answers``, ``usage``, optional
``request_id``, and ``elapsed_seconds`` (including retries).

* ``noul`` answers contain a ``noul`` probability between zero and one. Zero is
  a valid result, not an empty response.
* ``choice`` answers contain ``choice``, per-label ``probabilities``, and
  optional provider ``confidence``.
* ``score`` answers contain a fractional ``score``, ``probabilities``, a
  zero-based ``legend``, and optional ``confidence``. Rubric keys are strings
  in the normalized Python result as well as its JSON form.

Confidence is preserved separately from the selected label's probability.
LWE requires every question to have an answer of the correct type, checks
allowed labels and complete distributions, and verifies scores against the
supplied rubric and distribution. Invalid responses raise ``DecisionError``.
Input/configuration validation raises ``ValueError`` (including Pydantic's
``ValidationError``).

Applications own thresholds and fallback behavior. A valid answer can still be
wrong. Evaluate thresholds on representative labeled data and provide a path
for uncertain results. Include an ``other`` choice when appropriate.

Profile configuration
---------------------

Decision presets use the existing LWE profile's ``config.yaml`` but have their
own namespace. They are not conversational model presets:

.. code-block:: yaml

    decisions:
      presets:
        clef-triage:
          provider: cloudflare
          model: clef-omni
          options:
            account_id: your-account-id
          api_key_env_var: CLOUDFLARE_API_TOKEN
          timeout: 30.0
          max_retries: 2
        jev-triage:
          provider: typesafe
          model: jev-latest

Load a preset from the default LWE profile with
``DecisionSettings.from_preset("clef-triage")``. To select a different LWE profile,
use ``DecisionSettings.from_preset("clef-triage", profile="production")``.
The first argument is the preset name; the optional keyword selects the profile
whose ``config.yaml`` contains it. No profile field is required in the preset.
Explicit ``config_dir`` and ``data_dir`` parameters override ``LWE_CONFIG_DIR``
and ``LWE_DATA_DIR``. Loading a profile does not construct a chat backend or
connect to a conversation database. Missing credentials are reported only when
executing a decision.

Ansible workflows
-----------------

.. code-block:: yaml

    - name: Classify the request
      lwe_decide:
        preset: clef-triage
        state: "{{ support_request }}"
        questions:
          urgent:
            type: noul
            instructions: Does this require urgent attention?
      register: triage

    - name: Show the urgent request
      ansible.builtin.debug:
        msg: "Urgent: {{ support_request }}"
      when: not triage.skipped | default(false) and triage.answers.urgent.noul >= 0.9

Alternatively pass ``settings: {provider: cloudflare, model: clef-omni}`` instead
of ``preset``. Exactly one is required. ``profile`` defaults to ``default``.
The result fields are returned directly: use ``triage.answers``, not
``triage.response``. Successful classification reports ``changed: false``.
Ansible check mode validates the request and provider capabilities, returns
``skipped: true``, and makes no API call or credential lookup. It returns no
fabricated answers. Use ``no_log: true`` on tasks processing sensitive state
if you also need to suppress Ansible's own argument and result display.

Adding a provider
-----------------

Implement ``DecisionProvider.validate(request, settings)`` without network
access or credential resolution, ``prepare(request, settings)`` to resolve
external inputs once, and ``invoke(request, settings)`` returning
``model``, ``answers``, ``usage``, and optional ``request_id``. Normalize provider
responses to JSON-compatible dictionaries before returning them. Raise a
sanitized ``DecisionError``; mark only transient failures ``retryable=True``.

Register a no-argument provider class using a ``lwe_decision_providers`` package
entry point whose name matches ``DecisionSettings.provider``. The service loads
only the requested provider and rejects ambiguous duplicate registrations.
Provider-specific configuration belongs in ``settings.options``. Validate
unknown options explicitly. Providers manage their own HTTP client resources;
the service owns common response validation and retry policy.

The core ``MediaLoader`` handles HTTP(S) URLs, absolute local ``file://`` URIs,
base64 data URLs, and raw base64 strings. Plugins define supported modalities,
MIME types, counts, and decoded byte limits with ``MediaPolicy``, ``MediaLimits``,
and ``CombinedMediaLimit``. Core imposes no provider-specific media limits.
Call ``request.validate_media(policy)`` during validation, then call it with
``resolve=True`` and an optional loader during preparation. The returned request
contains normalized media; the caller's original request is unchanged.
Validation inspects embedded data but does not download URLs or read files.
Preparation errors identify the affected modality and item index. The loader
enforces byte budgets during reads and infers MIME types from binary signatures,
falling back to explicit data-URL types, HTTP headers, or file extensions.
