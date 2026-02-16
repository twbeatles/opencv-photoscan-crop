#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Line Interface for Photo Cropper v9.0.

Provides CLI access to batch processing functionality.
Usage: python -m photo_cropper.cli --help
"""

import argparse
import os
import sys
import json
import logging
from pathlib import Path

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

    # Detection mode + debug (v9.x accuracy)
    parser.add_argument(
        '--detect-mode',
        choices=['fast', 'balanced', 'accurate'],
        default='balanced',
        help='Detection mode preset (default: balanced)'
    )

    parser.add_argument(
        '--debug-detect',
        action='store_true',
        help='Save detection debug artifacts (stage images, overlays, meta.json)'
    )

    parser.add_argument(
        '--debug-dir',
        default='',
        help='Directory to store debug artifacts (default: output/_debug or TEMP)'
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
        version='Photo Cropper v9.0'
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


def parse_resize_arg(resize_arg: str):
    """Parse resize argument into core resize settings dict."""
    if not resize_arg:
        return None

    value = resize_arg.strip().lower()

    # Percentage (e.g., 50%)
    if value.endswith('%'):
        try:
            percentage = float(value.rstrip('%'))
        except ValueError:
            return None
        if percentage <= 0:
            return None
        return {"mode": "percentage", "percentage": percentage}

    # WxH (e.g., 800x600)
    if 'x' in value:
        parts = value.split('x')
        if len(parts) == 2:
            try:
                width = int(parts[0])
                height = int(parts[1])
            except ValueError:
                return None
            if width > 0 and height > 0:
                return {"mode": "fit", "width": width, "height": height}

    # Preset name
    try:
        from photo_cropper.core.resize_processor import ResizeProcessor
        if value in ResizeProcessor.PRESETS:
            width, height = ResizeProcessor.PRESETS[value]
            return {"mode": "fit", "width": width, "height": height}
    except Exception:
        return None

    return None


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
        AppSettings,
        AlgorithmSettings,
        DebugSettings,
        ProcessingSettings,
        OutputSettings,
        WatermarkSettings,
        ResizeSettings,
        FilterSettings,
        FileManagementSettings,
        MultiPhotoSettings,
        PerformanceSettings,
    )
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
        detection_mode=args.detect_mode,
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
    
    watermark_settings = WatermarkSettings(
        enabled=bool(args.watermark),
        text=args.watermark or "",
        position=args.watermark_position,
        opacity=args.watermark_opacity
    )

    resize_settings = ResizeSettings()
    if args.max_size > 0:
        resize_settings.enabled = True
        resize_settings.mode = "max_dimension"
        resize_settings.max_dimension = args.max_size
    elif args.resize:
        parsed_resize = parse_resize_arg(args.resize)
        if parsed_resize:
            resize_settings.enabled = True
            resize_settings.mode = parsed_resize.get("mode", "none")
            resize_settings.width = parsed_resize.get("width", 0)
            resize_settings.height = parsed_resize.get("height", 0)
            resize_settings.percentage = parsed_resize.get("percentage", 100.0)
        else:
            logger.warning(f"Invalid resize option: {args.resize}")

    filter_settings = FilterSettings(
        skip_small_images=True,
        min_image_size=args.min_size,
        skip_processed=args.skip_processed
    )

    file_management_settings = FileManagementSettings(
        recursive_search=args.recursive
    )

    multi_photo_settings = MultiPhotoSettings(
        enabled=args.multi_photo
    )

    jobs = max(1, args.jobs)
    performance_settings = PerformanceSettings(
        enable_multithreading=jobs > 1,
        thread_count=jobs
    )

    debug_settings = DebugSettings(
        enabled=bool(args.debug_detect),
        output_dir=(args.debug_dir or "").strip(),
    )

    settings = AppSettings(
        algorithm=algorithm_settings,
        processing=processing_settings,
        output=output_settings,
        debug=debug_settings,
        watermark=watermark_settings,
        resize=resize_settings,
        filter=filter_settings,
        file_management=file_management_settings,
        multi_photo=multi_photo_settings,
        performance=performance_settings
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
    
    def cli_log(message: str, level: str = "info"):
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

    processor = BatchProcessor(settings)
    processor.set_callbacks(
        on_log=cli_log
    )

    processor.start_async(args.input, output_dir, file_list=files)
    processor.wait_for_completion()

    results = processor.results
    success_count = len([r for r in results if r.status.name == "SUCCESS"])
    fail_count = len([r for r in results if r.status.name == "FAILED"])
    
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
