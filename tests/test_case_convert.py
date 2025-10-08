from __future__ import annotations

import unittest

from openspeleo_lib.utils import camel2snakecase
from openspeleo_lib.utils import snake2camelcase


class TestCaseConversion(unittest.TestCase):
    def test_camel2snakecase_basic(self):
        # Basic cases
        assert camel2snakecase("CamelCase") == "camel_case"
        assert camel2snakecase("CamelCaseTest") == "camel_case_test"
        assert camel2snakecase("Camel") == "camel"
        assert camel2snakecase("CamelCaseTestExample") == "camel_case_test_example"

    def test_camel2snakecase_edge_cases(self):
        # Single words and acronyms
        assert camel2snakecase("camel") == "camel"
        assert camel2snakecase("Camel") == "camel"
        assert camel2snakecase("IPhone") == "iphone"
        assert camel2snakecase("iPhone15") == "i_phone_15"
        assert camel2snakecase("A") == "a"
        assert camel2snakecase("TestA") == "test_a"
        assert camel2snakecase("APIResponse") == "apiresponse"

    def test_camel2snakecase_with_numbers(self):
        # Camel case with numbers
        assert camel2snakecase("Test1Value") == "test_1_value"
        assert camel2snakecase("TestValue123") == "test_value_123"
        assert camel2snakecase("Test123Value") == "test_123_value"

    def test_camel2snakecase_complex_cases(self):
        # Complex and mixed cases
        assert camel2snakecase("camelWith123Numbers") == "camel_with_123_numbers"
        # double underscore retained
        assert camel2snakecase("CamelC__with_dbl_udscr") == "camel_c__with_dbl_udscr"
        assert camel2snakecase("TestValueAnotherTest") == "test_value_another_test"

    def test_snake2camelcase_basic(self):
        # Basic cases
        assert snake2camelcase("snake_case") == "snakeCase"
        assert snake2camelcase("snake_case_test") == "snakeCaseTest"
        assert snake2camelcase("snake") == "snake"
        assert snake2camelcase("snake_case_test_example") == "snakeCaseTestExample"

    def test_snake2camelcase_edge_cases(self):
        # Single words and edge cases
        assert snake2camelcase("snake") == "snake"
        # assuming input is lowercase, we expect it to normalize
        assert snake2camelcase("Snake") == "snake"
        assert snake2camelcase("a") == "a"
        assert snake2camelcase("test_a") == "testA"
        assert snake2camelcase("api_response") == "apiResponse"
        assert snake2camelcase("response") == "response"

    def test_snake2camelcase_with_numbers(self):
        # Snake case with numbers
        assert snake2camelcase("test1_value") == "test1Value"
        assert snake2camelcase("test_value_123") == "testValue123"
        assert snake2camelcase("test_123_value") == "test123Value"
        assert snake2camelcase("snake_case_with_123_nbrs") == "snakeCaseWith123Nbrs"

    def test_snake2camelcase_complex_cases(self):
        # Complex and mixed cases
        assert (
            snake2camelcase("snake_case_with__double_underscore")
            == "snakeCaseWithDoubleUnderscore"
        )
        assert (
            snake2camelcase("camel_case_with_123_numbers") == "camelCaseWith123Numbers"
        )
        assert snake2camelcase("test_value_another_test") == "testValueAnotherTest"
        assert (
            snake2camelcase("snake_case_with__leading_and_trailing_underscores_")
            == "snakeCaseWithLeadingAndTrailingUnderscores"
        )

    def test_round_trip_conversion(self):
        # Round-trip conversion should result in original value
        original = "testCaseWith123Numbers"
        round_trip = snake2camelcase(camel2snakecase(original))
        assert original == round_trip, f"Round-trip failed: {round_trip} != {original}"

        original = "test_case_with_123_numbers"
        round_trip = camel2snakecase(snake2camelcase(original))
        assert original == round_trip, f"Round-trip failed: {round_trip} != {original}"

    def test_round_trip_conversion_edge_cases(self):
        # Round-trip for edge cases
        assert snake2camelcase(camel2snakecase("A")) == "a"
        assert snake2camelcase(camel2snakecase("IPhone")) == "iphone"

        assert camel2snakecase(snake2camelcase("a")) == "a"
        assert camel2snakecase(snake2camelcase("http_request")) == "http_request"

    def test_round_trip_conversion_complex_cases(self):
        # Round-trip for complex cases
        original = "complexCaseWith123NumbersAndApiCalls"
        round_trip = snake2camelcase(camel2snakecase(original))
        assert round_trip == original, f"Round-trip failed: {round_trip} != {original}"

        original = "complex_case_with_123_numbers_and_api_calls"
        round_trip = camel2snakecase(snake2camelcase(original))
        assert round_trip == original, f"Round-trip failed: {round_trip} != {original}"


if __name__ == "__main__":
    unittest.main()
