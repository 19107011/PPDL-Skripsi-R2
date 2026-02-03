"""

PPDL - Prediksi Pemakaian Daya Listrik
PPDL - Electrical Power Consumption Prediction

Academic Project Title:
Prediksi Pemakaian Daya Listrik Pada Rumah Tangga di Jakarta Berbasis IoT
dengan Menggunakan Metode Fuzzy Time Series

Prediction of Household Electrical Power Consumption in Jakarta
Using the Fuzzy Time Series Method

Property of:
Universitas Trilogi | Teknik Informatika | Program Sarjana (Strata 1)
Trilogi University | Informatics Engineering | Bachelor Degree

Author:
Alma Zannuba Arifah | 19107011

Supervisors:
Ir. Yaddarabulah, M.Kom., Ph.D.
Opitasari, S.Si., M.Kom.

Module:
System Resource Manager

Version: 1.0.1
Created: December 2025
"""

import atexit
import os
import shutil
import tempfile
import time
from pathlib import Path


class ResourceManager:
	"""Enhanced cache/temp folder manager for PPDL application sessions.

	Provides comprehensive cache management including:
	- Session-based temp directory creation and cleanup
	- Orphaned cache cleanup from previous sessions
	- Cache size monitoring and statistics
	- Robust error handling with logging integration
	- Complete cleanup verification with retry logic

	Usage Examples:
		# Basic temp directory usage
		temp_dir = ResourceManager.get_temp_dir()
		run_dir = ResourceManager.create_run_dir("W9Z7NUQ99V")

		# Manual cleanup
		ResourceManager.cleanup()

		# Startup orphaned cache cleanup
		ResourceManager.cleanup_orphaned_caches()

		# Monitor cache usage
		stats = ResourceManager.get_cleanup_stats()
		print(f"Active caches: {stats['cache_count']}")

		# Integration testing
		ResourceManager.integration_test()

	Error Handling:
		- PermissionError: Handles locked files gracefully
		- FileNotFoundError: Manages already-deleted directories
		- OSError: Filesystem-specific error recovery
		- Automatic fallback to print if AppLogger unavailable
	"""

	_temp_dir: str | None = None

	@classmethod
	def get_temp_dir(cls) -> str:
		"""Mengembalikan path folder temp sesi ini (membuat jika belum ada)."""

		if cls._temp_dir is None:
			cls._temp_dir = tempfile.mkdtemp(prefix="ppdl_cache_")
			print(f"[INFO] Temp Cache Created: {cls._temp_dir}")
		return cls._temp_dir

	@classmethod
	def get_runs_dir(cls) -> str:
		"""Folder root untuk semua artefak per-run di dalam temp sesi."""

		base = cls.get_temp_dir()
		runs_dir = os.path.join(base, "runs")
		os.makedirs(runs_dir, exist_ok=True)
		return runs_dir

	@classmethod
	def create_run_dir(cls, run_guid: str) -> str:
		"""Membuat folder khusus untuk satu run berdasarkan GUID."""

		safe_guid = str(run_guid).strip().upper()
		run_dir = os.path.join(cls.get_runs_dir(), safe_guid)
		os.makedirs(run_dir, exist_ok=True)
		return run_dir

	@classmethod
	def cleanup(cls) -> None:
		"""Enhanced cleanup with comprehensive error handling."""
		try:
			from utils.app_logger import AppLogger
			logger = AppLogger()
		except Exception:
			logger = None
		
		if cls._temp_dir and os.path.exists(cls._temp_dir):
			path = cls._temp_dir
			
			try:
				# Get directory size for stats
				total_size = sum(
					f.stat().st_size for f in Path(path).rglob('*') if f.is_file()
				) / (1024 * 1024)  # Convert to MB
				
				if logger:
					logger.log("INFO", f"Starting cache cleanup: {path}")
				else:
					print(f"[INFO] Starting cache cleanup: {path}")
				
				# Direct synchronous cleanup
				shutil.rmtree(path, ignore_errors=False)
				
				# Verification with timeout
				max_retries = 3
				for i in range(max_retries):
					if not os.path.exists(path):
						if logger:
							logger.log("INFO", f"Cache cleanup successful: {total_size:.2f}MB freed")
						else:
							print(f"[SUCCESS] Cache cleaned: {path} ({total_size:.2f}MB freed)")
						cls._temp_dir = None
						return
					time.sleep(0.5)  # Brief wait for filesystem
					
				if logger:
					logger.log("WARNING", f"Cache cleanup incomplete: {path}")
				else:
					print(f"[WARNING] Cache cleanup incomplete: {path}")
					
			except PermissionError as e:
				if logger:
					logger.log("ERROR", f"Permission denied during cache cleanup: {e}")
				else:
					print(f"[ERROR] Permission denied cleaning cache: {e}")
			except FileNotFoundError:
				if logger:
					logger.log("INFO", "Cache directory already removed")
				else:
					print(f"[INFO] Cache directory already removed: {path}")
				cls._temp_dir = None
			except OSError as e:
				if logger:
					logger.log("ERROR", f"Filesystem error during cache cleanup: {e}")
				else:
					print(f"[ERROR] Filesystem error during cache cleanup: {e}")
			except Exception as e:
				if logger:
					logger.log("ERROR", f"Unexpected error during cache cleanup: {e}")
				else:
					print(f"[ERROR] Failed to clean cache: {e}")
		else:
			if logger:
				logger.log("INFO", "No cache directory to clean")
			else:
				print("[INFO] No cache to clean")

	@classmethod
	def cleanup_orphaned_caches(cls) -> None:
		"""Clean up orphaned cache directories from previous sessions.

		Scans system temp directory for ppdl_cache_* patterns and removes
		directories older than 24 hours. Calculates and reports size statistics.

		Features:
			- Age-based cleanup (24-hour threshold)
			- Individual and cumulative size tracking
			- Comprehensive error handling per directory
			- Detailed logging with CLEANUP context
			- Non-blocking cleanup (ignore_errors=True)

		Age Logic:
			- Uses st_mtime (modification time) for age calculation
			- Only removes caches > 24 hours old
			- Preserves recent caches from active/recent sessions

		Error Handling:
			- PermissionError: Individual directory permission issues
			- OSError: Filesystem-specific errors per directory
			- Exception: Unexpected errors per directory
			- Continues processing remaining directories on errors

		Example Usage:
			# Startup cleanup in main.py
			ResourceManager.cleanup_orphaned_caches()

			# Manual orphaned cache scan
			ResourceManager.cleanup_orphaned_caches()
		"""
		try:
			from utils.app_logger import AppLogger
			logger = AppLogger()
		except Exception:
			logger = None
		
		temp_root = Path(tempfile.gettempdir())
		pattern = "ppdl_cache_*"
		
		orphaned_count = 0
		total_freed_mb = 0.0
		
		for cache_dir in temp_root.glob(pattern):
			try:
				# Check if cache is older than 24 hours
				age_hours = (time.time() - cache_dir.stat().st_mtime) / 3600
				if age_hours > 24:
					# Calculate size before deletion
					try:
						dir_size_mb = sum(
							f.stat().st_size for f in cache_dir.rglob('*') if f.is_file()
						) / (1024 * 1024)
					except Exception:
						dir_size_mb = 0.0
					
					shutil.rmtree(cache_dir, ignore_errors=True)
					
					if logger:
						logger.log("INFO", f"Removed orphaned cache: {cache_dir} ({dir_size_mb:.2f}MB)", lvl2="CLEANUP")
					else:
						print(f"[CLEANUP] Removed orphaned cache: {cache_dir} ({dir_size_mb:.2f}MB)")
					
					orphaned_count += 1
					total_freed_mb += dir_size_mb
					
			except PermissionError as e:
				if logger:
					logger.log("ERROR", f"Permission denied cleaning orphaned cache {cache_dir}: {e}", lvl2="CLEANUP")
				else:
					print(f"[ERROR] Permission denied cleaning orphaned cache {cache_dir}: {e}")
			except OSError as e:
				if logger:
					logger.log("ERROR", f"Filesystem error cleaning orphaned cache {cache_dir}: {e}", lvl2="CLEANUP")
				else:
					print(f"[ERROR] Filesystem error cleaning orphaned cache {cache_dir}: {e}")
			except Exception as e:
				if logger:
					logger.log("ERROR", f"Failed to clean orphaned cache {cache_dir}: {e}", lvl2="CLEANUP")
				else:
					print(f"[ERROR] Failed to clean orphaned cache {cache_dir}: {e}")
		
		if orphaned_count > 0:
			if logger:
				logger.log("INFO", f"Cleaned {orphaned_count} orphaned cache directories ({total_freed_mb:.2f}MB freed)", lvl2="CLEANUP")
			else:
				print(f"[INFO] Cleaned {orphaned_count} orphaned cache directories ({total_freed_mb:.2f}MB freed)")
		else:
			if logger:
				logger.log("INFO", "No orphaned cache directories found", lvl2="CLEANUP")
			else:
				print("[INFO] No orphaned cache directories found")

	@classmethod
	def get_cleanup_stats(cls) -> dict:
		"""Get comprehensive cache cleanup statistics.

		Scans system temp directory and provides detailed statistics
		about current cache usage and state.

		Returns:
			dict: Statistics dictionary with keys:
				- 'cache_count': Number of ppdl_cache_* directories found
				- 'total_size_mb': Total size in MB across all caches
				- 'temp_dir_active': Boolean if current session has active cache
				- 'current_cache_path': Path to active cache or None

		Example Usage:
			stats = ResourceManager.get_cleanup_stats()
			print(f"Found {stats['cache_count']} cache directories")
			print(f"Total size: {stats['total_size_mb']:.2f}MB")
			if stats['temp_dir_active']:
				print(f"Active cache: {stats['current_cache_path']}")

		Error Handling:
			- Silently ignores filesystem errors during size calculation
			- Returns 0 size for inaccessible directories
			- Always returns valid dictionary structure
		"""
		temp_root = Path(tempfile.gettempdir())
		ppdl_caches = list(temp_root.glob("ppdl_cache_*"))
		
		total_size = 0
		for cache_dir in ppdl_caches:
			try:
				total_size += sum(
					f.stat().st_size for f in cache_dir.rglob('*') if f.is_file()
				)
			except Exception:
				pass
		
		return {
			'cache_count': len(ppdl_caches),
			'total_size_mb': total_size / (1024 * 1024),
			'temp_dir_active': cls._temp_dir is not None,
			'current_cache_path': cls._temp_dir
		}

	@classmethod
	def integration_test(cls) -> None:
		"""Complete integration test of cache cleanup system.

		Performs comprehensive end-to-end testing of all cleanup
		functionality including orphaned cleanup, cache creation,
		statistics monitoring, and verification.

		Test Steps:
			1. Clean up any existing orphaned caches
			2. Create new test cache directory
			3. Add test data to cache
			4. Monitor cache statistics
			5. Perform cleanup operation
			6. Verify complete cleanup via statistics
			7. Report PASSED/FAILED/ERROR status

		Logging:
			- Uses AppLogger with lvl2="TEST" context
			- Fallback to print statements if logger unavailable
			- Detailed logging of each test step
			- Clear pass/fail reporting

		Example Usage:
			# Run complete system validation
			ResourceManager.integration_test()

		Expected Output:
			=== Cache Cleanup Integration Test ===
			Created cache: /tmp/ppdl_cache_abc123
			Cache stats: {'cache_count': 1, 'total_size_mb': 0.01, ...}
			Final stats: {'cache_count': 0, 'total_size_mb': 0.0, ...}
			=== Integration Test PASSED ===
		"""
		try:
			from utils.app_logger import AppLogger
			logger = AppLogger()
		except Exception:
			logger = None
		
		if logger:
			logger.log("INFO", "=== Cache Cleanup Integration Test ===", lvl2="TEST")
		else:
			print("=== Cache Cleanup Integration Test ===")
		
		try:
			# 1. Check for orphaned caches
			cls.cleanup_orphaned_caches()
			
			# 2. Create new cache
			temp_dir = cls.get_temp_dir()
			if logger:
				logger.log("INFO", f"Created cache: {temp_dir}", lvl2="TEST")
			else:
				print(f"Created cache: {temp_dir}")
			
			# 3. Add test data
			test_file = os.path.join(temp_dir, "integration_test.txt")
			with open(test_file, 'w') as f:
				f.write("integration test data")
			
			# 4. Check stats
			stats = cls.get_cleanup_stats()
			if logger:
				logger.log("INFO", f"Cache stats: {stats}", lvl2="TEST")
			else:
				print(f"Cache stats: {stats}")
			
			# 5. Cleanup
			cls.cleanup()
			
			# 6. Verify complete cleanup
			final_stats = cls.get_cleanup_stats()
			if logger:
				logger.log("INFO", f"Final stats: {final_stats}", lvl2="TEST")
			else:
				print(f"Final stats: {final_stats}")
			
			# 7. Verify success
			if final_stats['cache_count'] == 0:
				if logger:
					logger.log("INFO", "=== Integration Test PASSED ===", lvl2="TEST")
				else:
					print("=== Integration Test PASSED ===")
			else:
				if logger:
					logger.log("WARNING", "=== Integration Test FAILED - Cache not cleaned ===", lvl2="TEST")
				else:
					print("=== Integration Test FAILED - Cache not cleaned ===")
					
		except Exception as e:
			if logger:
				logger.log("ERROR", f"Integration test failed: {e}", lvl2="TEST")
			else:
				print(f"=== Integration Test ERROR: {e} ===")


atexit.register(ResourceManager.cleanup)
