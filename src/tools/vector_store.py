from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings


class VectorStore:
    
    def __init__(self, persist_directory: str = "./data/vector_db"):
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        try:
            self.collection = self.client.get_collection("pipeline_failures")
        except:
            self.collection = self.client.create_collection(
                name="pipeline_failures",
                metadata={"description": "Historical pipeline failure patterns"}
            )
    
    def add_failure(self, failure_id: str, symptoms: str, root_cause: str, fix: str):
        self.collection.add(
            ids=[failure_id],
            documents=[symptoms],
            metadatas=[{
                "root_cause": root_cause,
                "fix": fix
            }]
        )
    
    def search_similar(self, symptoms: str, n_results: int = 3) -> List[Dict]:
        try:
            results = self.collection.query(
                query_texts=[symptoms],
                n_results=n_results
            )
            
            similar = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    similar.append({
                        'symptoms': doc,
                        'root_cause': results['metadatas'][0][i].get('root_cause'),
                        'fix': results['metadatas'][0][i].get('fix')
                    })
            
            return similar
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
    
    def seed_sample_data(self):
        samples = [
            {
                'id': 'fail_001',
                'symptoms': 'API rate limit exceeded, 429 errors',
                'root_cause': 'No retry logic, hitting rate limits',
                'fix': 'Add exponential backoff retry'
            },
            {
                'id': 'fail_002',
                'symptoms': 'Missing data in target table',
                'root_cause': 'Source schema changed, new fields not mapped',
                'fix': 'Update schema mapping configuration'
            },
            {
                'id': 'fail_003',
                'symptoms': 'Connection timeout to database',
                'root_cause': 'Database connection pool exhausted',
                'fix': 'Increase connection pool size'
            }
        ]
        
        for sample in samples:
            try:
                self.add_failure(
                    sample['id'],
                    sample['symptoms'],
                    sample['root_cause'],
                    sample['fix']
                )
            except:
                pass
