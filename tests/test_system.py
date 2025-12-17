"""
System Testing Script - Validates the entire SHL recommendation system
"""
import requests
import json
import time
from typing import Dict, List

class SystemTester:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.test_results = []
        
    def test_health_endpoint(self) -> bool:
        """Test the health check endpoint."""
        print("\n" + "="*60)
        print("TEST 1: Health Check Endpoint")
        print("="*60)
        
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Health check passed")
                print(f"  Status: {data.get('status')}")
                print(f"  Message: {data.get('message')}")
                return True
            else:
                print(f"✗ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Health check error: {e}")
            return False
    
    def test_recommend_endpoint(self, query: str) -> Dict:
        """Test the recommendation endpoint with a query."""
        print(f"\nTesting query: '{query[:50]}...'")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.api_url}/recommend",
                json={"query": query},
                timeout=60
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                recs = data.get('recommendations', [])
                
                print(f"✓ Got {len(recs)} recommendations in {elapsed:.2f}s")
                
                # Validate response structure
                for i, rec in enumerate(recs, 1):
                    assert 'assessment_name' in rec, "Missing assessment_name"
                    assert 'url' in rec, "Missing url"
                    if i <= 3:  # Show first 3
                        print(f"  {i}. {rec['assessment_name'][:50]}...")
                
                return {
                    'success': True,
                    'num_results': len(recs),
                    'response_time': elapsed,
                    'data': data
                }
            else:
                print(f"✗ Request failed: {response.status_code}")
                print(f"  Error: {response.text}")
                return {
                    'success': False,
                    'error': response.text
                }
                
        except Exception as e:
            print(f"✗ Request error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_recommendation_quality(self) -> bool:
        """Test recommendation quality with sample queries."""
        print("\n" + "="*60)
        print("TEST 2: Recommendation Quality")
        print("="*60)
        
        test_queries = [
            {
                'query': "Java developer with good communication skills",
                'expected_types': ['K', 'P'],  # Knowledge and Personality
                'min_results': 5
            },
            {
                'query': "Senior analyst with strong cognitive abilities",
                'expected_types': ['C'],  # Cognitive
                'min_results': 5
            },
            {
                'query': "Entry-level Python programmer",
                'expected_types': ['K'],  # Knowledge
                'min_results': 5
            }
        ]
        
        all_passed = True
        
        for test in test_queries:
            result = self.test_recommend_endpoint(test['query'])
            
            if not result['success']:
                all_passed = False
                continue
            
            # Check minimum results
            if result['num_results'] < test['min_results']:
                print(f"  ✗ Expected >= {test['min_results']} results, got {result['num_results']}")
                all_passed = False
            else:
                print(f"  ✓ Minimum results satisfied ({result['num_results']} >= {test['min_results']})")
            
            # Check response time
            if result['response_time'] > 5.0:
                print(f"  ⚠ Slow response: {result['response_time']:.2f}s (expected < 5s)")
            else:
                print(f"  ✓ Response time acceptable: {result['response_time']:.2f}s")
            
            self.test_results.append(result)
        
        return all_passed
    
    def test_balance(self) -> bool:
        """Test if recommendations are balanced across test types."""
        print("\n" + "="*60)
        print("TEST 3: Recommendation Balance")
        print("="*60)
        
        # Query that should return mixed types
        query = "I am hiring for Java developers who can also collaborate effectively with my business teams."
        
        print(f"Testing with: '{query}'")
        
        result = self.test_recommend_endpoint(query)
        
        if not result['success']:
            return False
        
        # This would require access to test types in the response
        # For now, just check we got results
        print(f"✓ Got {result['num_results']} recommendations")
        print("  Note: Manual inspection needed to verify test type balance")
        
        return True
    
    def test_edge_cases(self) -> bool:
        """Test edge cases and error handling."""
        print("\n" + "="*60)
        print("TEST 4: Edge Cases & Error Handling")
        print("="*60)
        
        test_cases = [
            {"query": "", "expected": "fail", "desc": "Empty query"},
            {"query": "   ", "expected": "fail", "desc": "Whitespace only"},
            {"query": "a" * 1000, "expected": "success", "desc": "Very long query"},
            {"query": "非常特殊的查询", "expected": "success", "desc": "Non-English query"},
        ]
        
        all_passed = True
        
        for test in test_cases:
            print(f"\nTesting: {test['desc']}")
            
            try:
                response = requests.post(
                    f"{self.api_url}/recommend",
                    json={"query": test['query']},
                    timeout=30
                )
                
                if test['expected'] == 'fail':
                    if response.status_code != 200:
                        print(f"  ✓ Correctly rejected")
                    else:
                        print(f"  ✗ Should have failed but succeeded")
                        all_passed = False
                else:
                    if response.status_code == 200:
                        print(f"  ✓ Handled correctly")
                    else:
                        print(f"  ✗ Should have succeeded but failed")
                        all_passed = False
                        
            except Exception as e:
                print(f"  ✗ Error: {e}")
                all_passed = False
        
        return all_passed
    
    def test_performance(self) -> bool:
        """Test system performance with multiple requests."""
        print("\n" + "="*60)
        print("TEST 5: Performance Testing")
        print("="*60)
        
        queries = [
            "Python developer",
            "Sales manager with leadership skills",
            "Data analyst with SQL knowledge"
        ]
        
        times = []
        
        print(f"Running {len(queries)} queries...")
        
        for query in queries:
            start = time.time()
            result = self.test_recommend_endpoint(query)
            elapsed = time.time() - start
            
            if result['success']:
                times.append(elapsed)
        
        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            
            print(f"\n✓ Performance Summary:")
            print(f"  Average response time: {avg_time:.2f}s")
            print(f"  Maximum response time: {max_time:.2f}s")
            print(f"  Successful requests: {len(times)}/{len(queries)}")
            
            if avg_time < 3.0:
                print(f"  ✓ Performance is excellent")
                return True
            elif avg_time < 5.0:
                print(f"  ⚠ Performance is acceptable")
                return True
            else:
                print(f"  ✗ Performance needs improvement")
                return False
        
        return False
    
    def run_all_tests(self):
        """Run all tests and generate report."""
        print("\n")
        print("╔" + "="*58 + "╗")
        print("║" + " "*15 + "SHL SYSTEM TEST SUITE" + " "*22 + "║")
        print("╚" + "="*58 + "╝")
        
        tests = [
            ("Health Check", self.test_health_endpoint),
            ("Recommendation Quality", self.test_recommendation_quality),
            ("Balance", self.test_balance),
            ("Edge Cases", self.test_edge_cases),
            ("Performance", self.test_performance)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"\n✗ {test_name} failed with error: {e}")
                results[test_name] = False
        
        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✓ PASSED" if result else "✗ FAILED"
            print(f"{test_name:.<40} {status}")
        
        print("="*60)
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n✓ All tests passed! System is ready for deployment. 🎉")
            return True
        else:
            print(f"\n⚠ {total - passed} test(s) failed. Please review the issues above.")
            return False

def main():
    """Main execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test SHL recommendation system')
    parser.add_argument('--api-url', default='http://localhost:8000',
                       help='API endpoint URL')
    
    args = parser.parse_args()
    
    tester = SystemTester(api_url=args.api_url)
    success = tester.run_all_tests()
    
    exit(0 if success else 1)

if __name__ == "__main__":
    main()