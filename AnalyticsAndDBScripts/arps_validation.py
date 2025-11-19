"""
ARPS Decline Curve Validation Module

Provides automatic validation of ARPS curve fits to ensure mathematical correctness.
This module is integrated into the production pipeline to validate every curve fit.

Based on Arps (1945) decline curve theory.
"""

import numpy as np
import warnings


class ARPSValidationError(Exception):
    """Raised when ARPS validation fails critically"""
    pass


class ARPSValidator:
    """
    Validates ARPS decline curve fits against fundamental mathematical requirements
    """
    
    def __init__(self, strict_mode=False, log_warnings=True):
        """
        Args:
            strict_mode: If True, raise exceptions on validation failures
            log_warnings: If True, print warnings for validation issues
        """
        self.strict_mode = strict_mode
        self.log_warnings = log_warnings
        self.validation_results = {}
    
    def validate_fit(self, t_act, q_act, q_pred, qi_fit, dei_fit, b_fit, 
                     def_val, well_id=None, phase=None):
        """
        Comprehensive validation of an ARPS curve fit
        
        Args:
            t_act: Actual time array (must start at 0)
            q_act: Actual production rates
            q_pred: Predicted production rates
            qi_fit: Fitted initial rate
            dei_fit: Fitted initial effective decline
            b_fit: Fitted b-factor
            def_val: Terminal decline rate
            well_id: Well identifier (for logging)
            phase: Production phase (for logging)
        
        Returns:
            dict: Validation results with pass/fail status for each test
        """
        
        results = {
            'well_id': well_id,
            'phase': phase,
            'tests': {},
            'overall_pass': True,
            'warnings': [],
            'errors': []
        }
        
        # TEST 1: Time array starts at zero
        test1_pass = self._validate_time_zero(t_act, results)
        
        # TEST 2: First point alignment (q(0) ≈ Qi)
        test2_pass = self._validate_first_point(q_act, q_pred, qi_fit, results)
        
        # TEST 3: Decline trend (rates should decrease)
        test3_pass = self._validate_decline_trend(q_pred, results)
        
        # TEST 4: Goodness of fit
        test4_pass = self._validate_goodness_of_fit(q_act, q_pred, results)
        
        # TEST 5: Parameter reasonableness
        test5_pass = self._validate_parameters(qi_fit, dei_fit, b_fit, def_val, results)
        
        # TEST 6: Residual analysis
        test6_pass = self._validate_residuals(q_act, q_pred, results)
        
        # Overall pass/fail
        results['overall_pass'] = all([
            test1_pass, test2_pass, test3_pass, 
            test4_pass, test5_pass, test6_pass
        ])
        
        # Log results
        if self.log_warnings and (results['warnings'] or results['errors']):
            self._log_results(results)
        
        # Raise exception in strict mode if failed
        if self.strict_mode and not results['overall_pass']:
            error_msg = f"ARPS validation failed for Well {well_id} {phase}"
            if results['errors']:
                error_msg += f": {'; '.join(results['errors'])}"
            raise ARPSValidationError(error_msg)
        
        self.validation_results = results
        return results
    
    def _validate_time_zero(self, t_act, results):
        """Validate that time array starts at 0"""
        test_name = 'time_starts_at_zero'
        
        if len(t_act) == 0:
            results['tests'][test_name] = False
            results['errors'].append("Time array is empty")
            return False
        
        first_time = t_act[0]
        tolerance = 0.01
        
        if abs(first_time) > tolerance:
            results['tests'][test_name] = False
            results['errors'].append(
                f"Time array does not start at 0 (t[0]={first_time:.4f}). "
                "This violates ARPS equation requirement q(0)=Qi."
            )
            return False
        
        results['tests'][test_name] = True
        return True
    
    def _validate_first_point(self, q_act, q_pred, qi_fit, results):
        """Validate that q(0) ≈ Qi"""
        test_name = 'first_point_alignment'
        
        if len(q_pred) == 0 or len(q_act) == 0:
            results['tests'][test_name] = False
            results['errors'].append("Empty rate arrays")
            return False
        
        q_pred_0 = q_pred[0]
        q_act_0 = q_act[0]
        
        # Calculate error
        error_pct = abs(q_pred_0 - q_act_0) / q_act_0 * 100 if q_act_0 > 0 else 100
        
        results['tests'][test_name] = {
            'pass': error_pct < 15.0,
            'q_actual_0': q_act_0,
            'q_pred_0': q_pred_0,
            'qi_fit': qi_fit,
            'error_pct': error_pct
        }
        
        if error_pct > 15.0:
            results['warnings'].append(
                f"First point mismatch: q_pred(0)={q_pred_0:.2f}, "
                f"q_actual(0)={q_act_0:.2f}, error={error_pct:.1f}%"
            )
            return False
        elif error_pct > 10.0:
            results['warnings'].append(
                f"First point alignment acceptable but not ideal: error={error_pct:.1f}%"
            )
        
        return True
    
    def _validate_decline_trend(self, q_pred, results):
        """Validate that predicted rates show declining trend"""
        test_name = 'decline_trend'
        
        if len(q_pred) < 2:
            results['tests'][test_name] = True  # Can't test with <2 points
            return True
        
        # Check for increases (allow small noise)
        increases = []
        for i in range(1, len(q_pred)):
            if q_pred[i] > q_pred[i-1] * 1.05:  # More than 5% increase
                increases.append((i, q_pred[i-1], q_pred[i]))
        
        results['tests'][test_name] = {
            'pass': len(increases) == 0,
            'num_increases': len(increases),
            'increases': increases[:3]  # Store first 3
        }
        
        if increases:
            results['warnings'].append(
                f"Predicted rates increased at {len(increases)} points "
                "(expected monotonic decline)"
            )
            return False
        
        return True
    
    def _validate_goodness_of_fit(self, q_act, q_pred, results):
        """Validate goodness of fit metrics"""
        test_name = 'goodness_of_fit'
        
        # Calculate R²
        ss_res = np.sum((q_act - q_pred) ** 2)
        ss_tot = np.sum((q_act - np.mean(q_act)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Calculate RMSE
        rmse = np.sqrt(np.mean((q_act - q_pred) ** 2))
        
        # Calculate MAE
        mae = np.mean(np.abs(q_act - q_pred))
        
        results['tests'][test_name] = {
            'pass': r2 > 0.70,
            'r2': r2,
            'rmse': rmse,
            'mae': mae
        }
        
        if r2 < 0.70:
            results['warnings'].append(
                f"Poor fit: R²={r2:.3f} (expected >0.70)"
            )
            return False
        elif r2 < 0.85:
            results['warnings'].append(
                f"Acceptable fit: R²={r2:.3f} (good fit is >0.85)"
            )
        
        return True
    
    def _validate_parameters(self, qi_fit, dei_fit, b_fit, def_val, results):
        """Validate that fitted parameters are reasonable"""
        test_name = 'parameter_reasonableness'
        
        issues = []
        
        # Check Qi is positive
        if qi_fit <= 0:
            issues.append(f"Qi={qi_fit:.2f} must be positive")
        
        # Check Dei is in reasonable range (0 to 100% per year)
        if dei_fit < 0 or dei_fit > 1.0:
            issues.append(f"Dei={dei_fit:.4f} outside valid range [0, 1]")
        
        # Check b-factor is in reasonable range
        if b_fit < 0 or b_fit > 2.0:
            issues.append(f"b={b_fit:.4f} outside typical range [0, 2]")
        
        # Check Dei > Def (initial decline should be higher than terminal)
        if dei_fit < def_val:
            issues.append(
                f"Dei={dei_fit:.4f} < Def={def_val:.4f} "
                "(initial decline should exceed terminal)"
            )
        
        results['tests'][test_name] = {
            'pass': len(issues) == 0,
            'qi': qi_fit,
            'dei': dei_fit,
            'b': b_fit,
            'def': def_val,
            'issues': issues
        }
        
        if issues:
            results['warnings'].extend(issues)
            return False
        
        return True
    
    def _validate_residuals(self, q_act, q_pred, results):
        """Validate residual distribution"""
        test_name = 'residual_analysis'
        
        residuals = q_act - q_pred
        mean_residual = np.mean(residuals)
        std_residual = np.std(residuals)
        
        # Check for systematic bias (mean should be near zero)
        bias_threshold = std_residual * 0.5
        has_bias = abs(mean_residual) > bias_threshold
        
        results['tests'][test_name] = {
            'pass': not has_bias,
            'mean_residual': mean_residual,
            'std_residual': std_residual,
            'max_residual': np.max(np.abs(residuals))
        }
        
        if has_bias:
            results['warnings'].append(
                f"Systematic bias detected: mean residual={mean_residual:.2f}, "
                f"std={std_residual:.2f}"
            )
            return False
        
        return True
    
    def _log_results(self, results):
        """Log validation results"""
        well_id = results.get('well_id', 'Unknown')
        phase = results.get('phase', 'Unknown')
        
        if results['errors']:
            print(f"\n{'='*70}")
            print(f"ARPS VALIDATION ERRORS - Well {well_id} {phase}")
            print(f"{'='*70}")
            for error in results['errors']:
                print(f"  ✗ ERROR: {error}")
        
        if results['warnings']:
            print(f"\n{'='*70}")
            print(f"ARPS VALIDATION WARNINGS - Well {well_id} {phase}")
            print(f"{'='*70}")
            for warning in results['warnings']:
                print(f"  ⚠ WARNING: {warning}")
            
            # Print test summary
            print(f"\nTest Summary:")
            for test_name, test_result in results['tests'].items():
                if isinstance(test_result, dict):
                    status = "✓ PASS" if test_result.get('pass', False) else "✗ FAIL"
                else:
                    status = "✓ PASS" if test_result else "✗ FAIL"
                print(f"  {test_name:<30} {status}")
    
    def get_summary_stats(self):
        """Get summary statistics from last validation"""
        if not self.validation_results:
            return None
        
        tests = self.validation_results.get('tests', {})
        
        # Extract key metrics
        gof = tests.get('goodness_of_fit', {})
        first_pt = tests.get('first_point_alignment', {})
        
        return {
            'overall_pass': self.validation_results.get('overall_pass', False),
            'r2': gof.get('r2', None),
            'rmse': gof.get('rmse', None),
            'mae': gof.get('mae', None),
            'first_point_error_pct': first_pt.get('error_pct', None),
            'num_warnings': len(self.validation_results.get('warnings', [])),
            'num_errors': len(self.validation_results.get('errors', []))
        }


def validate_arps_fit(t_act, q_act, q_pred, qi_fit, dei_fit, b_fit, def_val,
                      well_id=None, phase=None, strict_mode=False):
    """
    Convenience function to validate an ARPS curve fit
    
    Args:
        t_act: Actual time array
        q_act: Actual production rates
        q_pred: Predicted production rates
        qi_fit: Fitted initial rate
        dei_fit: Fitted initial effective decline
        b_fit: Fitted b-factor
        def_val: Terminal decline rate
        well_id: Well identifier (optional)
        phase: Production phase (optional)
        strict_mode: If True, raise exception on validation failure
    
    Returns:
        dict: Validation results
    """
    validator = ARPSValidator(strict_mode=strict_mode, log_warnings=True)
    return validator.validate_fit(
        t_act, q_act, q_pred, qi_fit, dei_fit, b_fit, def_val,
        well_id=well_id, phase=phase
    )
