#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Line Interface for Photo Cropper v8.5.

Provides CLI access to batch processing functionality.
Usage: python -m photo_cropper.cli --help
"""

import argparse
import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_path():
    """Add package to path."""
    package_dir = Path(__file__).parent.parent
    if str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog='photo_cropper',
        description='Photo Cropper - Automatic photo detection and cropping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input ./scans --output ./cropped
  %(prog)s --input ./scans --output ./cropped --format png --quality 95
  %(prog)s --input ./scans --preset high_quality
  %(prog)s --input ./scans --config settings.json
        """
    )
    
    # Required arguments
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input folder containing images to process'
    )
    
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output folder for processed images (default: input folder)'
    )
    
    # Processing options
    parser.add_argument(
        '-f', '--format',
        choices=['jpg', 'png', 'webp'],
        default='jpg',
        help='Output image format (default: jpg)'
    )
    
    parser.add_argument(
        '-q', '--quality',
        type=int,
        default=95,
        help='Output quality for JPG/WebP (1-100, default: 95)'
    )
    
    parser.add_argument(
        '--compression',
        type=int,
        default=6,
        help='PNG compression level (0-9, default: 6)'
    )
    
    # Algorithm options
    parser.add_argument(
        '--canny-min',
        type=int,
        default=50,
        help='Canny edge detection minimum threshold (default: 50)'
    )
    
    parser.add_argument(
        '--canny-max',
        type=int,
        default=150,
        help='Canny edge detection maximum threshold (default: 150)'
    )
    
    parser.add_argument(
        '--no-clahe',
        action='store_true',
        help='Disable CLAHE contrast enhancement'
    )
    
    parser.add_argument(
        '--no-multi-scale',
        action='store_true',
        help='Disable multi-scale edge detection'
    )
    
    parser.add_argument(
        '--corner-detection',
        action='store_true',
        help='Enable Harris corner detection'
    )
    
    # Post-processing options
    parser.add_argument(
        '--grayscale',
        action='store_true',
        help='Convert output to grayscale'
    )
    
    parser.add_argument(
        '--sharpen',
        action='store_true',
        help='Apply sharpening to output'
    )
    
    parser.add_argument(
        '--denoise',
        action='store_true',
        help='Apply noise reduction'
    )
    
    # Watermark options
    parser.add_argument(
        '--watermark',
        default=None,
        help='Text watermark to add'
    )
    
    parser.add_argument(
        '--watermark-position',
        choices=['top_left', 'top_center', 'top_right',
                 'middle_left', 'center', 'middle_right',
                 'bottom_left', 'bottom_center', 'bottom_right'],
        default='bottom_right',
        help='Watermark position (default: bottom_right)'
    )
    
    parser.add_argument(
        '--watermark-opacity',
        type=float,
        default=0.5,
        help='Watermark opacity (0.0-1.0, default: 0.5)'
    )
    
    # Resize options
    parser.add_argument(
        '--resize',
        default=None,
        help='Resize output (e.g., "800x600", "50%%", or preset name)'
    )
    
    parser.add_argument(
        '--max-size',
        type=int,
        default=0,
        help='Maximum dimension in pixels (0 = no limit)'
    )
    
    # Multi-photo detection
    parser.add_argument(
        '--multi-photo',
        action='store_true',
        help='Detect and separate multiple photos per scan'
    )
    
    # Filter options
    parser.add_argument(
        '--skip-processed',
        action='store_true',
        help='Skip already processed files'
    )
    
    parser.add_argument(
        '--min-size',
        type=int,
        default=100,
        help='Minimum image size in pixels (default: 100)'
    )
    
    # Config file
    parser.add_argument(
        '-c', '--config',
        default=None,
        help='Path to JSON configuration file'
    )
    
    parser.add_argument(
        '--preset',
        default=None,
        help='Use a saved preset by name'
    )
    
    # Behavior options
    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Process subdirectories recursively'
    )
    
    parser.add_argument(
        '-j', '--jobs',
        type=int,
        default=4,
        help='Number of parallel processing jobs (default: 4)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without actually processing'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Photo Cropper v8.5'
    )
    
    return parser


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


def process_batch(args) -> int:
    """
    Process batch of images.
    
    Args:
        args: Parsed arguments
        
    Returns:
        Exit code (0 = success, 1 = error)
    """
    setup_path()
    
    # Import after path setup
    from photo_cropper.core.settings import (
        AppSettings, AlgorithmSettings, ProcessingSettings, OutputSettings
    )
    from photo_cropper.core.image_processor import ImageProcessor
    from photo_cropper.core.batch_processor import BatchProcessor
    from photo_cropper.utils.file_helpers import get_image_files
    
    # Validate input
    if not os.path.isdir(args.input):
        logger.error(f"Input directory not found: {args.input}")
        return 1
    
    output_dir = args.output or args.input
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Load config if specified
    config = {}
    if args.config:
        config = load_config(args.config)
    
    # Build settings
    algorithm_settings = AlgorithmSettings(
        canny_min=config.get('canny_min', args.canny_min),
        canny_max=config.get('canny_max', args.canny_max),
        use_clahe=not args.no_clahe,
        multi_scale_edge=not args.no_multi_scale,
        use_corner_detection=args.corner_detection
    )
    
    processing_settings = ProcessingSettings(
        to_grayscale=args.grayscale,
        apply_sharpening=args.sharpen,
        denoise=args.denoise
    )
    
    output_settings = OutputSettings(
        output_format=args.format.upper(),
        jpg_quality=args.quality,
        png_compression=args.compression,
        webp_quality=args.quality
    )
    
    settings = AppSettings(
        algorithm=algorithm_settings,
        processing=processing_settings,
        output=output_settings
    )
    
    # Get file list
    files = get_image_files(args.input, recursive=args.recursive)
    
    if not files:
        logger.warning("No image files found in input directory")
        return 0
    
    logger.info(f"Found {len(files)} images to process")
    
    if args.dry_run:
        logger.info("Dry run - files that would be processed:")
        for f in files:
            logger.info(f"  {f}")
        return 0
    
    # Create processor
    processor = BatchProcessor(settings)
    
    # Process files
    success_count = 0
    fail_count = 0
    
    for i, filename in enumerate(files, 1):
        filepath = os.path.join(args.input, filename)
        logger.info(f"[{i}/{len(files)}] Processing: {filename}")
        
        try:
            img_processor = ImageProcessor(
                algorithm_settings=algorithm_settings,
                processing_settings=processing_settings
            )
            
            result = img_processor.process_image(filepath)
            
            if result.success and result.image is not None:
                # Generate output filename
                base_name = os.path.splitext(filename)[0]
                output_name = f"{base_name}_cropped.{args.format}"
                output_path = os.path.join(output_dir, output_name)
                
                # Apply watermark if specified
                if args.watermark:
                    from photo_cropper.core.watermark_processor import (
                        WatermarkProcessor, TextWatermarkSettings, WatermarkPosition
                    )
                    
                    watermark_proc = WatermarkProcessor()
                    wm_settings = TextWatermarkSettings(
                        text=args.watermark,
                        opacity=args.watermark_opacity,
                        position=WatermarkPosition(args.watermark_position)
                    )
                    result.image = watermark_proc.apply_text_watermark(
                        result.image, wm_settings
                    )
                
                # Apply resize if specified
                if args.resize or args.max_size > 0:
                    from photo_cropper.core.resize_processor import (
                        ResizeProcessor, ResizeSettings, ResizeMode
                    )
                    
                    resize_proc = ResizeProcessor()
                    
                    if args.max_size > 0:
                        resize_settings = ResizeSettings(
                            enabled=True,
                            mode=ResizeMode.MAX_DIMENSION,
                            max_dimension=args.max_size
                        )
                    else:
                        resize_settings = ResizeSettings(
                            enabled=True,
                            mode=ResizeMode.PERCENTAGE,
                            percentage=float(args.resize.rstrip('%'))
                        )
                    
                    resize_result = resize_proc.resize(result.image, resize_settings)
                    if resize_result.success:
                        result.image = resize_result.image
                
                # Save result
                img_processor.save_image(
                    result.image,
                    output_path,
                    output_settings.output_format,
                    output_settings.jpg_quality,
                    output_settings.png_compression,
                    output_settings.webp_quality
                )
                
                logger.info(f"  ✓ Saved: {output_name} ({result.detection_stage.value})")
                success_count += 1
            else:
                logger.warning(f"  ✗ Failed: {result.message}")
                fail_count += 1
                
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            fail_count += 1
    
    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info(f"Processing complete!")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed:  {fail_count}")
    logger.info(f"  Total:   {len(files)}")
    
    return 0 if fail_count == 0 else 1


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        exit_code = process_batch(args)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
