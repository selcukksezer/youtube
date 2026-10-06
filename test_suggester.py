import sys
import json
import logging
logging.basicConfig(level=logging.DEBUG)

from services.topic_suggester import suggest_topics

def test():
    result = suggest_topics(niche_id="ancient_remedies_egypt", language="tr", count=5)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test()
