from gliner2 import AutoExtractor

model = AutoExtractor.from_pretrained("fastino/gliner2-base-v1")

text = """
Sarah manages the AI Development department.
The department owns Project Atlas.
Project Atlas uses Pinecone for vector storage.
"""

entities = model.extract_entities(
    text,
    ["person", "department", "project", "technology"]
)

print(entities)

text = """
John Smith works at Microsoft.
Microsoft developed Azure.
Azure is a cloud computing platform.
"""

relations = model.extract_relations(
    text,
    [
        "works_at",
        "developed",
        "is_a"
    ]
)

print(relations)