"use client";

import { useReportWebVitals } from 'next/web-vitals';
import { reportWebVital } from '@/lib/performance';

export default function PerformanceMonitor() {
  useReportWebVitals((metric) => {
    reportWebVital(metric);
  });

  return null;
}
