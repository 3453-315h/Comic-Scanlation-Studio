"""
Batch Processing Module - Comic Translation Studio

Processes multiple pages sequentially or in parallel with progress tracking,
carrying explicit page outcomes and failure counts.
"""

import logging
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass, field
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
class PageOutcome:
    """Outcome of processing an individual page."""
    page_id: str
    status: str  # "success", "partial", "failed"
    error: Optional[str] = None
    error_details: List[str] = field(default_factory=list)
    failed_bubbles_count: int = 0
    translated_bubbles_count: int = 0
    empty_bubbles_count: int = 0
    total_bubbles_count: int = 0


class BatchResult(list):
    """List of Page objects that also carries explicit outcomes and aggregate counts."""
    def __init__(self, pages: List[Page], outcomes: Dict[str, PageOutcome]):
        super().__init__(pages)
        self.outcomes: Dict[str, PageOutcome] = outcomes
        self.success_count: int = sum(1 for o in outcomes.values() if o.status == "success")
        self.partial_count: int = sum(1 for o in outcomes.values() if o.status == "partial")
        self.failure_count: int = sum(1 for o in outcomes.values() if o.status == "failed")
        self.total_count: int = len(pages)


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
    - Sequential or parallel processing with status tracking
    - Explicit page outcome contract (success, partial, failed)
    - Per-page error handling (failures don't stop batch)
    - Progress callbacks for UI integration
    - Summary of completed/failed pages
    """
    
    def __init__(self, pipeline: ScanlationPipeline):
        self.pipeline = pipeline
        self._cancel_requested = False
        
    def cancel(self):
        """Request cancellation of batch processing"""
        self._cancel_requested = True
        logger.info("Batch processing cancellation requested")
        
    def process_pages(self, 
                      pages: List[Page], 
                      project: Project,
                      progress_callback: Optional[Callable[[BatchProgress], None]] = None) -> BatchResult:
        """
        Process multiple pages sequentially through the pipeline.
        
        Args:
            pages: List of Page objects to process
            project: Project containing the pages
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchResult containing processed Page objects and aggregate outcomes.
        """
        self._cancel_requested = False
        total = len(pages)
        completed_pages: List[str] = []
        failed_pages: Dict[str, str] = {}
        processed_pages: List[Page] = []
        outcomes: Dict[str, PageOutcome] = {}
        
        logger.info(f"Starting batch processing of {total} pages")
        
        for i, page in enumerate(pages):
            if self._cancel_requested:
                logger.info("Batch processing cancelled by user")
                break
                
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
            
            try:
                logger.info(f"Processing page {i + 1}/{total}: {page.file_path}")
                result = self.pipeline.process_page(page, project)
                
                p_status = getattr(result, 'status', 'success')
                failed_cnt = getattr(result, 'failed_bubbles_count', sum(1 for b in result.bubbles if getattr(b, 'status', None) == 'failed'))
                trans_cnt = getattr(result, 'translated_bubbles_count', sum(1 for b in result.bubbles if getattr(b, 'status', None) == 'translated'))
                empty_cnt = getattr(result, 'empty_bubbles_count', sum(1 for b in result.bubbles if getattr(b, 'status', None) == 'ocr_empty'))
                tot_cnt = getattr(result, 'total_bubbles_count', len(result.bubbles))
                err_details = getattr(result, 'error_details', [])
                err = getattr(result, 'error', None)

                # A page with one or more failed bubbles cannot be counted as fully successful
                if p_status == "failed" or (tot_cnt > 0 and failed_cnt == tot_cnt):
                    p_status = "failed"
                    failed_pages[page.id] = err or "; ".join(err_details) or "All bubbles failed"
                elif p_status == "partial" or failed_cnt > 0:
                    p_status = "partial"
                    completed_pages.append(page.id)
                else:
                    p_status = "success"
                    completed_pages.append(page.id)

                result.status = p_status
                outcome = PageOutcome(
                    page_id=page.id,
                    status=p_status,
                    error=err,
                    error_details=err_details,
                    failed_bubbles_count=failed_cnt,
                    translated_bubbles_count=trans_cnt,
                    empty_bubbles_count=empty_cnt,
                    total_bubbles_count=tot_cnt,
                )
                result.outcome = outcome
                outcomes[page.id] = outcome
                processed_pages.append(result)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to process page {page.id}: {error_msg}")
                page.status = "failed"
                page.error = error_msg
                page.error_details = [error_msg]
                page.failed_bubbles_count = len(page.bubbles)
                page.total_bubbles_count = len(page.bubbles)
                outcome = PageOutcome(
                    page_id=page.id,
                    status="failed",
                    error=error_msg,
                    error_details=[error_msg],
                    failed_bubbles_count=len(page.bubbles),
                    translated_bubbles_count=0,
                    empty_bubbles_count=0,
                    total_bubbles_count=len(page.bubbles),
                )
                page.outcome = outcome
                outcomes[page.id] = outcome
                failed_pages[page.id] = error_msg
                processed_pages.append(page)
        
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
        
        logger.info(f"Batch processing complete: {len(completed_pages)}/{total} completed, {len(failed_pages)} failed")
        return BatchResult(processed_pages, outcomes)
    
    def process_pages_parallel(self,
                               pages: List[Page],
                               project: Project,
                               max_workers: int = 2,
                               progress_callback: Optional[Callable[[BatchProgress], None]] = None) -> BatchResult:
        """
        Process pages in parallel using a thread pool.
        """
        self._cancel_requested = False
        total = len(pages)
        completed_pages: List[str] = []
        failed_pages: Dict[str, str] = {}
        results: Dict[str, Page] = {}
        outcomes: Dict[str, PageOutcome] = {}
        
        logger.info(f"Starting parallel batch processing of {total} pages with {max_workers} workers")
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
                page.error = str(e)
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
                    p_status = getattr(result, 'status', 'success')
                    failed_cnt = getattr(result, 'failed_bubbles_count', sum(1 for b in result.bubbles if getattr(b, 'status', None) == 'failed'))
                    trans_cnt = getattr(result, 'translated_bubbles_count', sum(1 for b in result.bubbles if getattr(b, 'status', None) == 'translated'))
                    empty_cnt = getattr(result, 'empty_bubbles_count', sum(1 for b in result.bubbles if getattr(b, 'status', None) == 'ocr_empty'))
                    tot_cnt = getattr(result, 'total_bubbles_count', len(result.bubbles))
                    err_details = getattr(result, 'error_details', [])
                    err = getattr(result, 'error', None)

                    if p_status == "failed" or (tot_cnt > 0 and failed_cnt == tot_cnt):
                        p_status = "failed"
                        failed_pages[page.id] = err or "; ".join(err_details) or "All bubbles failed"
                    elif p_status == "partial" or failed_cnt > 0:
                        p_status = "partial"
                        completed_pages.append(page.id)
                    else:
                        p_status = "success"
                        completed_pages.append(page.id)

                    result.status = p_status
                    outcome = PageOutcome(
                        page_id=page.id,
                        status=p_status,
                        error=err,
                        error_details=err_details,
                        failed_bubbles_count=failed_cnt,
                        translated_bubbles_count=trans_cnt,
                        empty_bubbles_count=empty_cnt,
                        total_bubbles_count=tot_cnt,
                    )
                    result.outcome = outcome
                    outcomes[page.id] = outcome
                    results[page.id] = result
                except Exception as e:
                    error_msg = str(e)
                    page.status = "failed"
                    page.error = error_msg
                    page.error_details = [error_msg]
                    page.failed_bubbles_count = len(page.bubbles)
                    page.total_bubbles_count = len(page.bubbles)
                    outcome = PageOutcome(
                        page_id=page.id,
                        status="failed",
                        error=error_msg,
                        error_details=[error_msg],
                        failed_bubbles_count=len(page.bubbles),
                        translated_bubbles_count=0,
                        empty_bubbles_count=0,
                        total_bubbles_count=len(page.bubbles),
                    )
                    page.outcome = outcome
                    outcomes[page.id] = outcome
                    failed_pages[page.id] = error_msg
                    results[page.id] = page
                
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
        
        ordered_pages = [results.get(page.id, page) for page in pages]
        return BatchResult(ordered_pages, outcomes)


def process_batch(pipeline: ScanlationPipeline,
                  pages: List[Page],
                  project: Project,
                  progress_callback: Optional[Callable[[BatchProgress], None]] = None) -> BatchResult:
    """
    Convenience function for batch processing.
    """
    processor = BatchProcessor(pipeline)
    return processor.process_pages(pages, project, progress_callback)
