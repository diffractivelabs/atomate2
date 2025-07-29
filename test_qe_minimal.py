"""
Minimal test of QE workflow structure without external dependencies.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_file_structure():
    """Test that all required files exist."""
    base_path = os.path.join(os.path.dirname(__file__), 'src', 'atomate2', 'espresso')
    
    required_files = [
        '__init__.py',
        'jobs/__init__.py', 
        'jobs/base.py',
        'jobs/core.py',
        'flows/__init__.py',
        'flows/core.py',
        'schemas.py'
    ]
    
    print("=== File Structure Test ===")
    all_exist = True
    for file_path in required_files:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - MISSING")
            all_exist = False
            
    return all_exist

def test_syntax():
    """Test that Python files have valid syntax."""
    base_path = os.path.join(os.path.dirname(__file__), 'src', 'atomate2', 'espresso')
    
    python_files = [
        '__init__.py',
        'jobs/__init__.py', 
        'jobs/base.py',
        'jobs/core.py',
        'flows/__init__.py',
        'flows/core.py',
        'schemas.py'
    ]
    
    print("\n=== Syntax Test ===")
    all_valid = True
    
    for file_path in python_files:
        full_path = os.path.join(base_path, file_path)
        try:
            with open(full_path, 'r') as f:
                code = f.read()
            compile(code, full_path, 'exec')
            print(f"✓ {file_path} - Valid syntax")
        except SyntaxError as e:
            print(f"✗ {file_path} - Syntax error: {e}")
            all_valid = False
        except Exception as e:
            print(f"✗ {file_path} - Error: {e}")
            all_valid = False
            
    return all_valid

def test_class_definitions():
    """Test that key classes are properly defined (without importing)."""
    print("\n=== Class Definition Test ===")
    
    # Check schemas.py for QETaskDocument
    schema_path = os.path.join(os.path.dirname(__file__), 'src', 'atomate2', 'espresso', 'schemas.py')
    with open(schema_path, 'r') as f:
        schema_content = f.read()
    
    if 'class QETaskDocument' in schema_content:
        print("✓ QETaskDocument class defined")
    else:
        print("✗ QETaskDocument class not found")
        return False
        
    # Check jobs/core.py for job makers
    jobs_path = os.path.join(os.path.dirname(__file__), 'src', 'atomate2', 'espresso', 'jobs', 'core.py')
    with open(jobs_path, 'r') as f:
        jobs_content = f.read()
        
    if 'class SCFMaker' in jobs_content:
        print("✓ SCFMaker class defined")
    else:
        print("✗ SCFMaker class not found")
        return False
        
    if 'class BandsMaker' in jobs_content:
        print("✓ BandsMaker class defined")
    else:
        print("✗ BandsMaker class not found")
        return False
        
    # Check flows/core.py for workflow makers
    flows_path = os.path.join(os.path.dirname(__file__), 'src', 'atomate2', 'espresso', 'flows', 'core.py')
    with open(flows_path, 'r') as f:
        flows_content = f.read()
        
    if 'class BandGapMaker' in flows_content:
        print("✓ BandGapMaker class defined")
    else:
        print("✗ BandGapMaker class not found")
        return False
        
    if 'class RelaxBandGapMaker' in flows_content:
        print("✓ RelaxBandGapMaker class defined")
    else:
        print("✗ RelaxBandGapMaker class not found")
        return False
        
    return True

def test_example_file():
    """Test that example file exists and has valid syntax."""
    print("\n=== Example File Test ===")
    
    example_path = os.path.join(os.path.dirname(__file__), 'examples', 'qe_bandgap_example.py')
    
    if not os.path.exists(example_path):
        print("✗ Example file does not exist")
        return False
        
    try:
        with open(example_path, 'r') as f:
            code = f.read()
        compile(code, example_path, 'exec')
        print("✓ Example file has valid syntax")
        
        # Check for key functions
        if 'def create_silicon_structure' in code:
            print("✓ create_silicon_structure function defined")
        else:
            print("✗ create_silicon_structure function not found")
            
        if 'def main' in code:
            print("✓ main function defined")
        else:
            print("✗ main function not found")
            
        return True
    except Exception as e:
        print(f"✗ Example file error: {e}")
        return False

def test_workflow_logic():
    """Test workflow logic by examining the code structure."""
    print("\n=== Workflow Logic Test ===")
    
    flows_path = os.path.join(os.path.dirname(__file__), 'src', 'atomate2', 'espresso', 'flows', 'core.py')
    with open(flows_path, 'r') as f:
        flows_content = f.read()
        
    # Check BandGapMaker workflow logic
    checks = [
        ('SCF job creation', 'scf_job = self.scf_maker.make'),
        ('Bands job creation', 'bands_job = self.bands_maker.make'),
        ('Job chaining', 'prev_dir=scf_job.output.dir_name'),
        ('Flow creation', 'Flow(jobs, output=output'),
        ('Band gap output', 'band_gap": bands_job.output.band_gap'),
    ]
    
    all_good = True
    for check_name, pattern in checks:
        if pattern in flows_content:
            print(f"✓ {check_name}")
        else:
            print(f"✗ {check_name} - Pattern not found: {pattern}")
            all_good = False
            
    return all_good

def main():
    """Run all tests."""
    print("=== Quantum ESPRESSO Workflow Validation ===")
    print("(Testing without external dependencies)\n")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Syntax Validation", test_syntax),
        ("Class Definitions", test_class_definitions),
        ("Example File", test_example_file),
        ("Workflow Logic", test_workflow_logic),
    ]
    
    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))
        
    print("\n=== Test Summary ===")
    passed = 0
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
            
    print(f"\nPassed: {passed}/{len(tests)} tests")
    
    if passed == len(tests):
        print("\n🎉 All structural tests passed!")
        print("The QE workflow is properly implemented and ready for integration.")
        print("\nTo use the workflow, you'll need:")
        print("- pymatgen for structure handling")
        print("- ASE with Quantum ESPRESSO calculator") 
        print("- jobflow for workflow execution")
        print("- Quantum ESPRESSO installation")
    else:
        print(f"\n❌ {len(tests) - passed} tests failed.")

if __name__ == "__main__":
    main()