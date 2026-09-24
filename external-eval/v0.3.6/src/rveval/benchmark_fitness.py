"""Benchmark validity and implementation compatibility are independent axes.

This module validates a recorded, source-referenced fitness review. It cannot
prove absence of contamination, and contains no benchmark-name allowlist.
"""
from .guardrails import require


def assess_benchmark_fitness(review, *, required=False):
    if review is None:
        return {'status': 'REVIEW_REQUIRED' if required else 'NOT_REQUESTED', 'fitness_established_by_runner': False}
    require(type(review) is dict, 'BENCHMARK_FITNESS_REVIEW_INVALID')
    require(review.get('status') in {'REVIEWED_APPROPRIATE', 'UNSUITABLE', 'REVIEW_REQUIRED'}, 'BENCHMARK_FITNESS_STATUS_INVALID')
    for field in ('purpose', 'benchmark_revision', 'reviewed_at', 'reason', 'sources'):
        require(bool(review.get(field)), 'BENCHMARK_FITNESS_PROVENANCE_REQUIRED')
    require(type(review['sources']) is list and all(type(s) is str and bool(s) for s in review['sources']), 'BENCHMARK_FITNESS_SOURCES_INVALID')
    require(review.get('purpose') in {'INSTALLATION_ONLY', 'TASK_COMPARISON', 'FRONTIER_CAPABILITY'}, 'BENCHMARK_FITNESS_PURPOSE_INVALID')
    if review['status'] == 'UNSUITABLE': status = 'UNSUITABLE'
    elif review['status'] == 'REVIEW_REQUIRED': status = 'REVIEW_REQUIRED'
    else: status = 'FITNESS_REVIEW_RECORDED'
    if required:
        require(review['purpose'] != 'INSTALLATION_ONLY', 'INSTALLATION_TEST_CANNOT_SUPPORT_CONFIRMATORY_CLAIM')
    return {'status': status, 'review': review, 'fitness_established_by_runner': False}
