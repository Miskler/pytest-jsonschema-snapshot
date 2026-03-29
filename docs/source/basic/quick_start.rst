Quick Start
===========

Install the package:
--------------------

.. code-block:: console

   pip install pytest-jsonschema-snapshot

Then you need to configure the library
--------------------------------------

Choose the option that best suits your project:

.. code-block:: ini

    # pytest.ini
    [pytest]
    jsss_dir = __snapshots__               # where to put the schemas
    jsss_callable_regex = {class_method=.} # rule for the callable part
    jsss_format_mode = on

.. code-block:: python

    # pyproject.toml
    [tool.pytest.ini_options]
    jsss_dir = "__snapshots__"
    jsss_callable_regex = "{class_method=.}"
    jsss_format_mode = "on"

.. code-block:: ini

    # setup.cfg
    [tool:pytest]
    jsss_dir = __snapshots__
    jsss_callable_regex = {class_method=.}
    jsss_format_mode = on

* **jsss_dir**: the name of the folder where the library will save the schemas/originals *(always in the same directory as the test that called it)*.
* **jsss_callable_regex**: the rule for interpreting the callable name.
* **jsss_format_mode**: "on" (annotate and validate), "safe" (annotate), "off" (disable).

Automatic schema generation is powered by `genschema`.
When you call :meth:`~pytest_jsonschema_snapshot.core.SchemaShot.assert_json_match`,
the plugin generates a schema from the observed JSON, enables format inference,
enables enum inference for short low-cardinality strings, and runs post-processing
that extracts repeated fragments into ``$defs``/``$ref``.

By contrast, :meth:`~pytest_jsonschema_snapshot.core.SchemaShot.assert_schema_match`
accepts your explicit JSON Schema as-is and only uses the merge/update pipeline when needed.

Next, you can use the fixture in your tests:
--------------------------------------------

.. code-block:: python

    from pytest_jsonschema_snapshot import SchemaShot

    def test_something(schemashot: SchemaShot):
        # There are data - need to validate through the schema
        schemashot.assert_json_match(
            {"key": "value"}, # data for validation / convert to schema
            "test_name"       # name of the schema
        )

        # There is a schema (data is optional) - validate by what is
        schemashot.assert_schema_match(
            {           # schema
                "$schema": "http://json-schema.org/schema#",
                "type": "object",
                "properties": {
                    "content": {
                        "type": "object"
                    }
                },
                "required": [
                    "content"
                ]
            },
            ("test_name", 1), # == `test_name.1` name of the schema
            data={"content": {"key": "value"}} # data for validation (optional)
        )

Names can be passed as a string, int, callable (function or method), or a tuple/array consisting of them.

Callable fields are converted using :class:`~pytest_jsonschema_snapshot.tools.name_maker.NameMaker` according to the rule specified by `jsss_callable_regex`.
For how to correctly define your own rules, see :class:`~pytest_jsonschema_snapshot.tools.name_maker.NameMaker`.


Run
---

.. code-block:: console

    pytest --jsss-debug --save-original --schema-update

* **--jsss-debug**: by default, the library hides its part of the call stack when raising. This is convenient for debugging your tests, but if the problem is in PJSSS itself - you can pass.
* **--save-original**: save the original data on which the validation was performed. Saving occurs when `--schema-update`, if you run the schema update without this attribute, the old original data will be deleted without saving new ones.

Modes of operation
* **--schema-update**: when updating **merges** two schemas. Works by principle: "what is valid for the old one, is valid for the new one, and vice versa"
* **--schema-reset**: when updating **replaces** the old schema with the new one.

Disabling update mechanisms
* **--without-delete**: disables deletion of old schemas
* **--without-update**: disables updating of existing schemas
* **--without-add**: disables adding new schemas

.. code-block:: console

    (.venv) miskler@MBook:~/pjsss$ pytest --jsss-debug --save-original --schema-update
    ...........................................                                                                                                                            [100%]
    ============== Schema Summary ==============
    Created schemas (6):
    - multi_schema_one.schema.json + original
    - multi_schema_two.schema.json + original
    - multi_schema_three.schema.json + original
    43 passed in 0.32s
