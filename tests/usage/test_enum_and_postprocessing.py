def test_enum_and_reference_postprocessing(schemashot):
    data = {
        "delivery_method": "pickup",
        "billing_address": {
            "street": "Main st",
            "city": "Moscow",
            "zip": "101000",
        },
        "shipping_address": {
            "street": "Oak st",
            "city": "Moscow",
            "zip": "101001",
        },
    }

    schemashot.assert_json_match(data, "enum_and_postprocess_test")
