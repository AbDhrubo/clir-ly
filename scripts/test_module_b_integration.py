"""
Module B Integration Test - Run on Colab
Test all query processing functions
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.query.detector import detect_language, is_mixed_language
from src.query.translator import translate_query
from src.query.processor import process_query


def test_detector():
    """Test language detection."""
    print("\n" + "="*60)
    print("TEST 1: Language Detection")
    print("="*60)
    
    tests = [
        ("Bangladesh politics", "en"),
        ("বাংলাদেশের রাজনীতি", "bn"),
        ("hello world", "en"),
        ("নমস্কার বিশ্ব", "bn"),
    ]
    
    passed = 0
    for text, expected in tests:
        result = detect_language(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} detect_language('{text[:30]}...') = {result} (expected {expected})")
        if result == expected:
            passed += 1
    
    print(f"\nResult: {passed}/{len(tests)} passed")
    return passed == len(tests)


def test_mixed_detection():
    """Test mixed language detection."""
    print("\n" + "="*60)
    print("TEST 2: Mixed Language Detection")
    print("="*60)
    
    tests = [
        ("Bangladesh এবং ভারত", True),   # Mixed
        ("বাংলাদেশ", False),               # Only Bangla
        ("Bangladesh", False),              # Only English
        ("আমি go করব", True),              # Mixed
    ]
    
    passed = 0
    for text, expected in tests:
        result = is_mixed_language(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} is_mixed_language('{text}') = {result} (expected {expected})")
        if result == expected:
            passed += 1
    
    print(f"\nResult: {passed}/{len(tests)} passed")
    return passed == len(tests)


def test_translator():
    """Test translation."""
    print("\n" + "="*60)
    print("TEST 3: Translation (English ↔ Bangla)")
    print("="*60)
    
    tests = [
        ("hello world", "en", "bn"),
        ("আমি খুশি", "bn", "en"),
        ("Bangladesh", "en", "bn"),
        ("বাংলাদেশ", "bn", "en"),
    ]
    
    passed = 0
    for text, src, tgt in tests:
        try:
            result = translate_query(text, src, tgt)
            if result and result != text:
                status = "✅"
                passed += 1
            else:
                status = "⚠️"
            print(f"{status} translate('{text}', {src}→{tgt}) = '{result}'")
        except Exception as e:
            print(f"❌ translate('{text}', {src}→{tgt}) ERROR: {e}")
    
    print(f"\nResult: {passed}/{len(tests)} working")
    return passed > 0


def test_processor():
    """Test full query processor."""
    print("\n" + "="*60)
    print("TEST 4: Full Query Processor")
    print("="*60)
    
    test_queries = [
        "Bangladesh politics",
        "বাংলাদেশের রাজনীতি",
        "Amir Khan actor",
        "আমির খান অভিনেতা",
    ]
    
    passed = 0
    for query in test_queries:
        try:
            result = process_query(query)
            
            # Check all required fields
            required = ['original', 'language', 'normalized', 'translated', 'both_versions', 'is_mixed']
            has_all = all(k in result for k in required)
            
            if has_all and result['language'] in ['en', 'bn']:
                status = "✅"
                passed += 1
            else:
                status = "❌"
            
            print(f"{status} process_query('{query[:30]}...')")
            print(f"     → Language: {result['language']}, Translated: {result['translated'][:30]}...")
            
        except Exception as e:
            print(f"❌ process_query('{query}') ERROR: {e}")
    
    print(f"\nResult: {passed}/{len(test_queries)} passed")
    return passed == len(test_queries)


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "MODULE B - Query Processing Tests" + " "*11 + "║")
    print("╚" + "="*58 + "╝")
    
    results = []
    
    try:
        results.append(("Language Detection", test_detector()))
    except Exception as e:
        print(f"❌ Language Detection failed: {e}")
        results.append(("Language Detection", False))
    
    try:
        results.append(("Mixed Language Detection", test_mixed_detection()))
    except Exception as e:
        print(f"❌ Mixed Language Detection failed: {e}")
        results.append(("Mixed Language Detection", False))
    
    try:
        results.append(("Translation", test_translator()))
    except Exception as e:
        print(f"❌ Translation failed: {e}")
        results.append(("Translation", False))
    
    try:
        results.append(("Query Processor", test_processor()))
    except Exception as e:
        print(f"❌ Query Processor failed: {e}")
        results.append(("Query Processor", False))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {total_passed}/{len(results)} test suites passed")
    
    if total_passed == len(results):
        print("\n🎉 All tests passed! Module B is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {len(results) - total_passed} test suite(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
