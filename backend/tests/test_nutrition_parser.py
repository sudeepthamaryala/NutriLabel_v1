from app.services.nutrition_parser import parse


def test_parse_ocr_noisy_nutrition_label():
    result = parse(
        """
        Serving Size 30g
        Energy 250 kcal
        Total Fat 8g
        Sodium 580 mg
        Total Sugars 12 g
        Protein 5g
        """
    )

    assert result.model_dump() == {
        "calories": 250.0,
        "total_fat_g": 8.0,
        "protein_g": 5.0,
        "sugar_g": 12.0,
        "sodium_mg": 580.0,
        "serving_size": "30g",
        "ingredients": [],
    }
