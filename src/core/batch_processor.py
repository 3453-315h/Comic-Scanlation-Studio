"""
Batch Processing Module - Comic Translation Studio

Processes multiple pages sequentially with progress tracking.
Based on 8-bit-magic-wand BatchMode implementation.
"""

import logging
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
import threading

from .project import Project, Page
from .pipeline import ScanlationPipeline

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Status of a page in the batch"""
    IDLE = "idle"
    DETECTING = "detecting"
    OCR = "ocr"
    TRANSLATING = "translating"
    INPAINTING = "inpainting"
    IMPRINTING = "imprinting"
    DONE = "done"
    ERROR = "error"


@dataclass
class BatchProgress:
    """Progress information for batch processing"""
    current_page: int
    total_pages: int
    current_page_id: str
    current_status: ProcessingStatus
    completed_pages: List[str]
    failed_pages: Dict[str, str]  # page_id -> error message
    
    @property
    def percent_complete(self) -> float:
        return (self.current_page / self.total_pages * 100) if self.total_pages > 0 else 0


class BatchProcessor:
    """
    Processes multiple comic pages through the scanlation pipeline.
    
    Features:
    - Sequential processing with status tracking
    - Per-page error handling (failures don't stop batch)
    - Progress callbacks for UI integration
    - Summary of completed/failed pages
    
    Usage:
        processor = BatchProcessor(pipeline)
        results = processor.process_pages(pages, project, progress_callback)
    """
    
    def __init__(self, pipeline: ScanlationPipeline):
        """
        Initialize batch processor.
        
        Args:
            pipeline: The scanlation pipeline to use for processing
        """
        self.pipeline = pipeline
        self._cancel_requested = False
        
    def cancel(self):
        """Request cancellation of batch processing"""
        self._cancel_requested = True
        logger.info("Batch processing cancellation requested")
        
    def process_pages(self, 
                      pages: List[Page], 
                      project: Project,
                      progress_callback: Optional[Callable[[BatchProgress], None]] = None) -> List[Page]:
        """
        Process multiple pages through the pipeline.
        
        Args:
            pages: List of Page objects to process
            project: Project containing the pages
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of processed Page objects
        """
        self._cancel_requested = False
        total = len(pages)
        completed_pages: List[str] = []
        failed_pages: Dict[str, str] = {}
        processed_pages: List[Page] = []
        
        logger.info(f"Starting batch processing of {total} pages")
        
        for i, page in enumerate(pages):
            # Check for cancellation
            if self._cancel_requested:
                logger.info("Batch processing cancelled by user")
                break
                
            # Update progress
            progress = BatchProgress(
                current_page=i + 1,
                total_pages=total,
                current_page_id=page.id,
                current_status=ProcessingStatus.DETECTING,
                completed_pages=completed_pages.copy(),
                failed_pages=failed_pages.copy()
            )
            
            if progress_callback:
                progress_callback(progress)
            
            # Process the page
            try:
                logger.info(f"Processing page {i + 1}/{total}: {page.file_path}")
                result = self.pipeline.process_page(page, project)
                processed_pages.append(result)
                completed_pages.append(page.id)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to process page {page.id}: {error_msg}")
                failed_pages[page.id] = error_msg
                processed_pages.append(page)  # Include with original state
        
        # Final progress update
        final_progress = BatchProgress(
            current_page=total,
            total_pages=total,
            current_page_id=pages[-1].id if pages else "",
            current_status=ProcessingStatus.DONE,
            completed_pages=completed_pages,
            failed_pages=failed_pages
        )
        
        if progress_callback:
            progress_callback(final_progress)
        
        # Log summary
        logger.info(f"Batch processing complete: {len(completed_pages)}/{total} succeeded, {len(failed_pages)} failed")
        
        return processed_pages
    
    def process_pages_parallel(self,
                               pages: List[Page],
                               project: Project,
                               max_workers: int = 2,
                               progress_callback: Optional[Callable[[BatchProgress], None]] = None) -> List[Page]:
        """
        Process pages in parallel using a thread pool.
        
        Note: Parallel processing may not be faster if the pipeline uses shared GPU resources.
        Use with caution for CPU-bound operations only.
        
        Args:
            pages: List of pages to process
            project: Project containing the pages
            max_workers: Maximum parallel workers
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of processed pages
        """
        self._cancel_requested = False
        total = len(pages)
        completed_pages: List[str] = []
        failed_pages: Dict[str, str] = {}
        results: Dict[str, Page] = {}
        
        logger.info(f"Starting parallel batch processing of {total} pages with {max_workers} workers")
        
        # Each worker thread gets its own pipeline instance to avoid sharing non-thread-safe models
        thread_local = threading.local()

        def process_single(page: Page) -> Page:
            try:
                pipeline = getattr(thread_local, "pipeline", None)
                if pipeline is None:
                    pipeline = ScanlationPipeline(self.pipeline.config)
                    thread_local.pipeline = pipeline
                return pipeline.process_page(page, project)
            except Exception as e:
                page.status = "failed"
                raise e
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures: Dict[Future, Page] = {}
            
            for page in pages:
                future = executor.submit(process_single, page)
                futures[future] = page
            
            for future in futures:
                page = futures[future]
                try:
                    result = future.result()
                    results[page.id] = result
                    completed_pages.append(page.id)
                except Exception as e:
                    failed_pages[page.id] = str(e)
                    results[page.id] = page
                
                # Progress update
                progress = BatchProgress(
                    current_page=len(completed_pages) + len(failed_pages),
                    total_pages=total,
                    current_page_id=page.id,
                    current_status=ProcessingStatus.DONE if page.id in completed_pages else ProcessingStatus.ERROR,
                    completed_pages=completed_pages.copy(),
                    failed_pages=failed_pages.copy()
                )
                
                if progress_callback:
                    progress_callback(progress)
        
        # Return in original order
        return [results.get(page.id, page) for page in pages]


def process_batch(pipeline: ScanlationPipeline,
                  pages: List[Page],
                  project: Project,
                  progress_callback: Optional[Callable[[BatchProgress], None]] = None) -> List[Page]:
    """
    Convenience function for batch processing.
    
    Args:
        pipeline: Pipeline to use
        pages: Pages to process
        project: Project context
        progress_callback: Optional progress callback
        
    Returns:
        Processed pages
    """
    processor = BatchProcessor(pipeline)
    return processor.process_pages(pages, project, progress_callback)
