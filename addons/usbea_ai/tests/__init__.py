# Odoo integration tests for usbea_ai go here, picked up by
#     odoo-bin -i usbea_ai --test-enable
#
# Pure-Python unit tests (services: LGPDRedactor, PromptCache, ModelRouter)
# live in ../tests_unit/ to avoid triggering the addon's Odoo imports during
# plain `pytest` runs.
