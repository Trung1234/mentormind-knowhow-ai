"""Provider layer shared by every kind (VLM in spec 04, LLM in spec 06).

``base``/``models`` (interface, config, usage), ``registry`` (name -> class), ``errors``,
``transport`` (HTTP + retry), ``openai_compat`` (vendor endpoints, locality), ``parsing`` (JSON).
"""
