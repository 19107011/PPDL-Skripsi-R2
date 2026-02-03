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
PNG Logo Preprocessing Tool

Version: 1.0.1
Created: December 2025
"""

#!/usr/bin/env python3
"""
PNG Logo Preprocessing Tool
Cleans alpha channel and removes semi-transparent background pixels.
Generates clean PNG asset for PDF watermarks.
"""

from PIL import Image
import os
import numpy as np

def clean_png_logo(input_path: str, output_path: str, alpha_threshold: int = 128) -> bool:
    """
    Clean PNG logo by removing semi-transparent background pixels.
    
    Args:
        input_path: Path to original PNG logo
        output_path: Path for cleaned output PNG
        alpha_threshold: Alpha value threshold (0-255). Pixels below this become fully transparent.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Open and convert to RGBA
        img = Image.open(input_path).convert("RGBA")
        
        # Convert to numpy array for pixel manipulation
        data = np.array(img)
        
        # Get RGBA channels
        red, green, blue, alpha = data.T
        
        # Create mask for semi-transparent background pixels
        # Typically background has low alpha or is whitish with medium alpha
        background_mask = (
            (alpha < alpha_threshold) |  # Low alpha pixels
            ((red > 240) & (green > 240) & (blue > 240) & (alpha < 255))  # Whitish semi-transparent
        )
        
        # Set background pixels to fully transparent
        data[..., 3][background_mask.T] = 0  # Set alpha to 0
        
        # Create cleaned image
        cleaned_img = Image.fromarray(data, 'RGBA')
        
        # Save as PNG with preserved transparency
        cleaned_img.save(output_path, "PNG", optimize=True)
        
        print(f"✅ Logo cleaned successfully:")
        print(f"   Input:  {input_path}")
        print(f"   Output: {output_path}")
        print(f"   Alpha threshold: {alpha_threshold}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning PNG logo: {e}")
        return False

def main():
    """Main preprocessing execution."""
    # Paths
    input_logo = r"D:\0.0.SKRIPSI-ALMA\JANUARY 2026\Aplikasi\ppdl-app\output_data\logo-trilogi.png"
    output_logo = r"D:\0.0.SKRIPSI-ALMA\JANUARY 2026\Aplikasi\ppdl-app\output_data\logo-trilogi-clean.png"
    
    # Check if input exists
    if not os.path.exists(input_logo):
        print(f"❌ Input logo not found: {input_logo}")
        return
    
    print("🔧 PNG Logo Preprocessing - RUN-1 & RUN-2 Enhancement")
    print("=" * 60)
    
    # Clean the logo
    success = clean_png_logo(input_logo, output_logo, alpha_threshold=128)
    
    if success:
        print("\n✅ Logo preprocessing completed!")
        print(f"📁 Clean logo ready: {output_logo}")
        print("\nNext: Update ExportManager to use cleaned asset.")
    else:
        print("\n❌ Preprocessing failed!")

if __name__ == "__main__":
    main()