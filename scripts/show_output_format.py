"""
Module C - Example Output Format
Shows what the retrieval output looks like
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def format_results_output(results, method_name: str, query: str):
    """Show how results are formatted."""
    
    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print(f"METHOD: {method_name}")
    print(f"{'='*80}\n")
    
    if not results:
        print("❌ No results found")
        return
    
    for rank, result in enumerate(results[:5], 1):
        # Format the result
        title = result.get('title', 'N/A')
        language = result.get('language', '?')
        score = result.get('score', 0)
        source = result.get('source', 'N/A')
        url = result.get('url', 'N/A')
        date = result.get('date', 'N/A')
        body = result.get('body', '')[:100]
        
        print(f"┌─ Rank #{rank} ─────────────────────────────────────────────────────────┐")
        print(f"│ Title:    {title[:60]}")
        print(f"│ Language: {language} | Source: {source} | Score: {score:.3f}")
        print(f"│ Date:     {date}")
        print(f"│ URL:      {url[:60]}...")
        print(f"│ Preview:  {body}...")
        print(f"└──────────────────────────────────────────────────────────────────────┘\n")


def show_mock_results():
    """Show example results."""
    
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "MODULE C - Example Retrieval Output" + " "*24 + "║")
    print("╚" + "="*78 + "╝")
    
    # Example results for "Bangladesh politics"
    mock_results_en = [
        {
            'title': 'Bangladesh Election Results 2024',
            'language': 'en',
            'score': 0.923,
            'source': 'daily_star',
            'url': 'https://thedailystar.net/politics/bangladesh-election-2024',
            'date': '2024-12-15',
            'body': 'The Bangladesh general election held on January 7, 2024, was a significant political event...'
        },
        {
            'title': 'রাজনীতিতে পরিবর্তনের হাওয়া',
            'language': 'bn',
            'score': 0.891,
            'source': 'prothom_alo',
            'url': 'https://prothomalo.com/bangladesh/politics',
            'date': '2024-12-10',
            'body': 'বাংলাদেশের রাজনীতিতে নতুন পরিবর্তন আসছে যা দেশের ভবিষ্যত নির্ধারণ করবে...'
        },
        {
            'title': 'Political Crisis in Dhaka',
            'language': 'en',
            'score': 0.856,
            'source': 'dhaka_tribune',
            'url': 'https://dhakatribune.com/politics',
            'date': '2024-12-08',
            'body': 'A new political crisis has emerged in Bangladesh as various parties clash over...'
        },
        {
            'title': 'বিরোধী দলের নতুন কৌশল',
            'language': 'bn',
            'score': 0.743,
            'source': 'bdnews24',
            'url': 'https://bangla.bdnews24.com/politics',
            'date': '2024-12-05',
            'body': 'বিরোধী দল নতুন কৌশল নিয়ে এগিয়ে আসছে যা দেশের রাজনৈতিক পরিবর্তন ঘটাতে পারে...'
        },
        {
            'title': 'Government Announces New Policy',
            'language': 'en',
            'score': 0.621,
            'source': 'new_age',
            'url': 'https://newagebd.com/politics',
            'date': '2024-12-01',
            'body': 'The Bangladesh government has announced a new political policy aimed at strengthening...'
        }
    ]
    
    print("\n" + "🔍 EXAMPLE 1: English Query")
    format_results_output(mock_results_en, "Hybrid Search", "Bangladesh politics")
    
    # Example for Bangla query
    mock_results_bn = [
        {
            'title': 'শিক্ষা ব্যবস্থায় নতুন সংস্কার',
            'language': 'bn',
            'score': 0.912,
            'source': 'prothom_alo',
            'url': 'https://prothomalo.com/education',
            'date': '2024-12-12',
            'body': 'বাংলাদেশে শিক্ষা ব্যবস্থায় বড় পরিবর্তন আসতে চলেছে যা শিক্ষার্থীদের জন্য হবে উপকারী...'
        },
        {
            'title': 'Education Reform Initiative Launched',
            'language': 'en',
            'score': 0.887,
            'source': 'daily_star',
            'url': 'https://thedailystar.net/education',
            'date': '2024-12-10',
            'body': 'Bangladesh has launched a comprehensive education reform initiative designed to improve...'
        },
        {
            'title': 'স্কুল-কলেজে নতুন পাঠ্যক্রম',
            'language': 'bn',
            'score': 0.834,
            'source': 'bdnews24',
            'url': 'https://bangla.bdnews24.com/education',
            'date': '2024-12-08',
            'body': 'স্কুল এবং কলেজে নতুন পাঠ্যক্রম চালু হবে যা আধুনিক শিক্ষা নিশ্চিত করবে...'
        },
        {
            'title': 'Academic Excellence Program',
            'language': 'en',
            'score': 0.756,
            'source': 'dhaka_tribune',
            'url': 'https://dhakatribune.com/education',
            'date': '2024-12-05',
            'body': 'A new academic excellence program has been introduced to help students achieve better...'
        },
        {
            'title': 'বিশ্ববিদ্যালয়ের মানোন্নয়ন প্রকল্প',
            'language': 'bn',
            'score': 0.698,
            'source': 'kaler_kantho',
            'url': 'https://www.kalerkantho.com/education',
            'date': '2024-11-30',
            'body': 'বিশ্ববিদ্যালয়ের মানোন্নয়নের জন্য নতুন প্রকল্প গ্রহণ করা হয়েছে...'
        }
    ]
    
    print("\n" + "🔍 EXAMPLE 2: Bangla Query")
    format_results_output(mock_results_bn, "Hybrid Search", "ঢাকায় শিক্ষা ব্যবস্থা")
    
    # Show data structure
    print("\n" + "="*80)
    print("JSON STRUCTURE (Raw Data)")
    print("="*80)
    
    print("\nEach result is a dictionary with this structure:")
    print(json.dumps(mock_results_en[0], indent=2, ensure_ascii=False))
    
    print("\n\nKEY FIELDS EXPLAINED:")
    print("  • title:    Article headline (in original language)")
    print("  • language: 'en' (English) or 'bn' (Bangla)")
    print("  • score:    Relevance score (0.0 - 1.0)")
    print("             1.0 = perfect match, 0.0 = no match")
    print("  • source:   Which news website it came from")
    print("  • url:      Link to the original article")
    print("  • date:     Publication date")
    print("  • body:     Full article text")
    print("  • ranking:  Position in results (1 = top result)")
    
    print("\n" + "="*80)
    print("WHAT THE SCORE MEANS:")
    print("="*80)
    print("  0.9 - 1.0:  Highly relevant (definitely what user wanted)")
    print("  0.7 - 0.9:  Very relevant (likely what user wanted)")
    print("  0.5 - 0.7:  Somewhat relevant (might be useful)")
    print("  0.3 - 0.5:  Loosely related (probably not what user wanted)")
    print("  0.0 - 0.3:  Irrelevant (should be ignored)")
    
    print("\n" + "="*80)
    print("CROSS-LINGUAL EXAMPLE:")
    print("="*80)
    print("\nQuery (English): 'Bangladesh cricket'")
    print("Can find both:")
    print("  ✅ 'Bangladesh Cricket Team Wins' (English)")
    print("  ✅ 'বাংলাদেশ ক্রিকেট দল জয়ী' (Bangla)")
    print("  ✅ 'ঢাকায় আন্তর্জাতিক ক্রিকেট ম্যাচ' (Bangla, related concept)")
    print("\nThis is the power of semantic/multilingual search!")


if __name__ == "__main__":
    show_mock_results()
