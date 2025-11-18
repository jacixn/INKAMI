#!/usr/bin/env python3
"""Test OCR locally on the downloaded image"""

from pathlib import Path
import sys
sys.path.append('/Users/jz/Desktop/github/INKAMI/apps/server')

from PIL import Image
import pytesseract
import cv2
import numpy as np

def test_ocr():
    image_path = Path('/tmp/page_new.webp')
    if not image_path.exists():
        print("❌ Image not found at /tmp/page_new.webp")
        return
    
    # Load image
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    print(f"📏 Image size: {width}x{height}")
    
    # Test basic OCR
    print("\n🔍 Running basic Tesseract OCR...")
    try:
        text = pytesseract.image_to_string(image)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        print(f"Found {len(lines)} lines of text")
        for i, line in enumerate(lines[:5]):  # Show first 5 lines
            print(f"  {i}: {line}")
    except Exception as e:
        print(f"❌ Tesseract error: {e}")
    
    # Test UI detection with color mask
    print("\n🎨 Testing blue UI detection...")
    try:
        # Convert to OpenCV format
        cv_image = np.array(image)
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
        
        # Define blue color range
        lower_blue = np.array([100, 0, 0])
        upper_blue = np.array([255, 100, 100])
        
        # Create mask
        mask = cv2.inRange(cv_image, lower_blue, upper_blue)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"Found {len(contours)} blue regions")
        
        # Process largest blue regions
        for i, contour in enumerate(sorted(contours, key=cv2.contourArea, reverse=True)[:3]):
            x, y, w, h = cv2.boundingRect(contour)
            print(f"\n  Blue region {i}: x={x}, y={y}, w={w}, h={h}")
            
            if w > 50 and h > 20:
                # Extract region
                region = image.crop((x, y, x+w, y+h))
                
                # Try OCR on the region
                try:
                    text = pytesseract.image_to_string(region).strip()
                    if text:
                        print(f"    Text: {text}")
                except:
                    print("    OCR failed on this region")
                    
    except Exception as e:
        print(f"❌ Blue detection error: {e}")

if __name__ == "__main__":
    test_ocr()
