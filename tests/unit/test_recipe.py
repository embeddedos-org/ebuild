from ebuild.packages.recipe import PackageRecipe


def test_package_recipe_to_dict_uses_canonical_schema():
    recipe = PackageRecipe(
        name="demo",
        version="1.0.0",
        url="https://example.com/demo.tar.gz",
        build_system="cmake",
        dependencies=["dep"],
    )

    data = recipe.to_dict()

    assert data["package"] == "demo"
    assert data["version"] == "1.0.0"
    assert data["url"] == "https://example.com/demo.tar.gz"
    assert data["build"] == "cmake"
    assert data["dependencies"] == ["dep"]
    assert "name" not in data
    assert "build_system" not in data