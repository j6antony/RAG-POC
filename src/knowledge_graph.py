import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

class KnowledgeGraph:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth = (
                os.environ["NEO4J_USERNAME"],
                os.environ["NEO4J_PASSWORD"]
            )
        )

        self.database = os.getenv("NEO4J_DATABASE", "neo4j")

        self.driver.execute_query(
            """
            CREATE CONSTRAINT entity_key IF NOT EXISTS
            FOR (e:Entity)
            REQUIRE e.key IS UNIQUE
            """,
            database_=self.database
        )

    def save(self, entities, relations, document_id, chunk_id, owner_id, access_level, classification):
        entity_records = []
        names = {}

        for entity_type, values in entities.get("entities", {}).items():
            for value in values:
                name = value["text"] if isinstance(value, dict) else value
                name = str(name).strip()

                if not name:
                    continue

                normalized = name.casefold()
                key = f"{owner_id}:{entity_type}:{normalized}"

                entity_records.append({
                    "key": key,
                    "name": name, 
                    "type": entity_type
                })

                names.setdefault(normalized, set()).add(key)
        relation_records = []

        for relation_type, pairs in relations.get(
            "relation_extraction", {}
        ).items():
            for pair in pairs:
                if isinstance(pair, dict):
                    source = pair["head"]["text"]
                    target = pair["tail"]["text"]
                else:
                    source, target = pair

                source_keys = names.get(str(source).strip().casefold(), set())
                target_keys = names.get(str(target).strip().casefold(), set())

                if len(source_keys) != 1 or len(target_keys) != 1:
                    continue

                relation_records.append({
                    "source": next(iter(source_keys)),
                    "target": next(iter(target_keys)),
                    "type": relation_type
                })

        # Save the chunk, entities, and relationships atomically
        with self.driver.session(database=self.database) as session:
            session.execute_write(
                self._save_transaction,
                entity_records,
                relation_records,
                str(document_id),
                str(chunk_id),
                str(owner_id),
                access_level,
                classification
            )

    @staticmethod
    def _save_transaction(
        tx,
        entities,
        relations,
        document_id,
        chunk_id,
        owner_id,
        access_level,
        classification
    ):
        tx.run(
            """
            MERGE (c:Chunk {id: $chunk_id})
            SET c.document_id = $document_id,
                c.owner_id = $owner_id,
                c.access_level = $access_level,
                c.classification = $classification
            """,
            chunk_id=chunk_id,
            document_id=document_id,
            owner_id=owner_id,
            access_level=access_level,
            classification=classification
        ).consume()

        tx.run(
            """
            MATCH (c:Chunk {id: $chunk_id})
            UNWIND $entities AS entity

            MERGE (e:Entity {key: entity.key})
            ON CREATE SET
                e.name = entity.name,
                e.type = entity.type

            MERGE (c)-[:MENTIONS]->(e)
            """,
            chunk_id=chunk_id,
            entities=entities
        ).consume()

        tx.run(
            """
            UNWIND $relations AS rel

            MATCH (source:Entity {key: rel.source})
            MATCH (target:Entity {key: rel.target})

            MERGE (source)-[r:RELATED_TO {
                type: rel.type,
                chunk_id: $chunk_id
            }]->(target)

            SET r.document_id = $document_id
            """,
            relations=relations,
            chunk_id=chunk_id,
            document_id=document_id
        ).consume()

    def close(self):
        self.driver.close()

    def search(self, entity_name: str, user_id: str, access_level: int, limit: int = 30):
        entity_name = entity_name.strip()
        if len(entity_name) < 2:
            return {"nodes": [], "links": []}

        query =  """MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)

    WHERE c.owner_id = $user_id
      AND c.access_level <= $access_level
      AND toLower(e.name) CONTAINS toLower($entity_name)

    MATCH (c)-[:MENTIONS]->(source:Entity)
          -[r:RELATED_TO]->(target:Entity)

    WHERE r.chunk_id = c.id
      AND (source = e OR target = e)
      AND EXISTS {
          MATCH (c)-[:MENTIONS]->(target)
      }

    RETURN DISTINCT
        source.key AS source_id,
        source.name AS source_name,
        source.type AS source_type,
        target.key AS target_id,
        target.name AS target_name,
        target.type AS target_type,
        r.type AS relationship,
        c.id AS chunk_id

    LIMIT $limit
    """

        records, _,  _ = self.driver.execute_query(
            query,
            entity_name = entity_name,
            user_id = str(user_id),
            access_level = access_level,
            limit = min(max(limit, 1), 100),
            database_=self.database,
            routing_ = "r"
        )

        nodes = {}
        links = []

        for record in records:
            source_id = record["source_id"]
            target_id = record["target_id"]

            nodes[source_id] = {
                "id": source_id,
                "name": record["source_name"],
                "type": record["source_type"]
            }

            nodes[target_id] = {
                "id": target_id,
                "name": record["target_name"],
                "type": record["target_type"]
            }

            links.append({
                "source": source_id,
                "target": target_id,
                "relationship": record["relationship"],
                "chunk_id": record["chunk_id"]
            })
        return {
            "nodes": list(nodes.values()),
            "links": links
        }
