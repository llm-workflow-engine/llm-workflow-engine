===============================================
Docker (experimental)
===============================================

Build a docker image for testing ``lwe``:

Make sure your OpenAI key has been exported into your host environment as ``OPENAI_API_KEY``

Run the following commands:

.. code-block:: bash

   docker-compose build && docker-compose up -d
   docker exec -it lwe-container /bin/bash -c "lwe"

Follow the instructions to create the first user.

Enjoy the chat!
