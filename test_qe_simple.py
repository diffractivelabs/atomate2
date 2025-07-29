"""
Simple test of QE workflow structure without running actual calculations.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that our QE modules can be imported."""
    try:
        from atomate2.espresso import BandGapMaker, RelaxBandGapMaker
        from atomate2.espresso.jobs.core import SCFMaker, BandsMaker
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_workflow_creation():
    """Test workflow creation without actual pymatgen structures."""
    try:
        from atomate2.espresso import BandGapMaker
        
        # Create workflow maker
        bg_maker = BandGapMaker(name="test workflow")
        print(f"✓ Created BandGapMaker: {bg_maker.name}")
        
        # Check that it has the expected attributes
        assert hasattr(bg_maker, 'scf_maker')
        assert hasattr(bg_maker, 'bands_maker')
        print("✓ BandGapMaker has expected attributes")
        
        return True
    except Exception as e:
        print(f"✗ Workflow creation failed: {e}")
        return False

def test_job_makers():
    """Test job maker creation."""
    try:
        from atomate2.espresso.jobs.core import SCFMaker, BandsMaker
        
        # Create job makers
        scf_maker = SCFMaker()
        bands_maker = BandsMaker()
        
        print(f"✓ SCFMaker created: {scf_maker.name}")
        print(f"✓ BandsMaker created: {bands_maker.name}")
        
        # Check input settings
        assert 'kpts' in scf_maker.input_settings
        assert 'ecutwfc' in scf_maker.input_settings
        print("✓ SCFMaker has expected input settings")
        
        assert 'kpts' in bands_maker.input_settings
        assert 'nbnd' in bands_maker.input_settings
        print("✓ BandsMaker has expected input settings")
        
        return True
    except Exception as e:
        print(f"✗ Job maker test failed: {e}")
        return False

def test_schemas():
    """Test schema imports."""
    try:
        from atomate2.espresso.schemas import QETaskDocument
        print("✓ QETaskDocument schema imported successfully")
        
        # Check schema fields
        fields = QETaskDocument.__fields__
        expected_fields = ['structure', 'energy', 'forces', 'band_gap', 'calculation_type']
        
        for field in expected_fields:
            if field in fields:
                print(f"✓ Schema has {field} field")
            else:
                print(f"✗ Schema missing {field} field")
                return False
                
        return True
    except Exception as e:
        print(f"✗ Schema test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Testing Quantum ESPRESSO Atomate2 Workflow ===\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Workflow Creation Test", test_workflow_creation), 
        ("Job Makers Test", test_job_makers),
        ("Schemas Test", test_schemas),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
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
        print("\n🎉 All tests passed! The QE workflow is ready to use.")
    else:
        print(f"\n❌ {len(tests) - passed} tests failed. Check the implementation.")

if __name__ == "__main__":
    main()