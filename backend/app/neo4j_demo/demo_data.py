from app.repository import seed_exhibits


neo4j_demo_exhibits = seed_exhibits
space_dome_exhibit = next(item for item in seed_exhibits if item.id == "space-dome")
