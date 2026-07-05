import type { WorkflowJobStatus, WorkflowJobType } from '$lib/api/deckService/workflow.client';

export type AdminAgentRun = {
  id: string;
  runType: string;
  status: string;
  deckId: string | null;
  deckTitle: string | null;
  userId: string | null;
  userEmail: string | null;
  workspaceId: string | null;
  workspaceName: string | null;
  provider: string | null;
  model: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  completedAt: string | null;
  selectedSlideCount: number;
  artifactCount: number;
  requestId: string | null;
  metadata: Record<string, unknown>;
};

export type AdminUserRole = 'super_admin' | 'admin' | 'user' | 'general';

export type AdminUser = {
  id: string;
  email: string;
  name: string;
  role: AdminUserRole;
  createdAt: string | null;
  updatedAt: string | null;
  // Backend uses snake_case for these fields; keep both for compatibility while rolling this in.
  created_at?: string | null;
  updated_at?: string | null;
  permissions?: Array<{
    resource: string;
    action: string;
    granted: boolean;
  }>;
};

export type AdminOverview = {
  summary: {
    users: number;
    workspaces: number;
    decks: number;
    authSessions: number;
    workspaceAiConfigured: number;
    auditEvents: number;
    agentRuns: number;
    agentRunsFailed: number;
    agentRunsRunning: number;
    agentRunsCompleted: number;
    aiUsageBuckets: number;
    rateLimitBuckets: number;
  };
  providerCounts: Record<string, number>;
  recentRuns: AdminAgentRun[];
  recentActivity: Array<{
    id: string;
    actorUserId: string | null;
    actorEmail: string | null;
    action: string;
    result: string;
    resourceType: string | null;
    resourceId: string | null;
    requestId: string | null;
    createdAt: string | null;
  }>;
};

export type AdminAgentRunsResponse = {
  runs: AdminAgentRun[];
  total: number;
};

export type AdminAgentRunNote = {
  id: string;
  actorUserId: string | null;
  actorEmail: string | null;
  note: string | null;
  runType: string | null;
  requestId: string | null;
  createdAt: string | null;
};

export type AdminAgentRunDetail = {
  run: AdminAgentRun;
  related: Record<string, unknown>;
  redaction: {
    sensitiveFieldsRedacted: string[];
    detailPolicy: string;
  };
  notes: AdminAgentRunNote[];
};

export type AdminLearningMemory = {
  id: string;
  workspaceId: string | null;
  workspaceName: string | null;
  deckId: string | null;
  deckTitle: string | null;
  userId: string | null;
  userEmail: string | null;
  sourceRunId: string | null;
  sourceRunType: string | null;
  memoryType: string;
  status: string;
  feedbackLabel: string | null;
  score: number;
  title: string;
  content: string;
  tags: string[];
  evidence: Record<string, unknown>;
  createdByUserId: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  lastUsedAt: string | null;
};

export type AdminLearningCandidateRun = {
  id: string;
  runType: string;
  status: string;
  deckId: string | null;
  deckTitle: string | null;
  workspaceId: string | null;
  workspaceName: string | null;
  userId: string | null;
  userEmail: string | null;
  provider: string | null;
  model: string | null;
  selectedSlideCount: number;
  errorPreview: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  completedAt: string | null;
};

export type AdminLearningMemoriesResponse = {
  summary: {
    total: number;
    returned: number;
    candidateRuns: number;
    reflectionCount: number;
    exemplarCount: number;
    insightCount: number;
  };
  typeCounts: Record<string, number>;
  statusCounts: Record<string, number>;
  memories: AdminLearningMemory[];
  candidateRuns: AdminLearningCandidateRun[];
  redaction: {
    sensitiveFieldsRedacted: string[];
    detailPolicy: string;
  };
};

export type AdminTelemetryEvent = {
  id: string;
  workspaceId: string | null;
  deckId: string | null;
  userId: string | null;
  runId: string | null;
  runType: string;
  stepId: string | null;
  eventName: string;
  eventLevel: string;
  status: string | null;
  provider: string | null;
  model: string | null;
  latencyMs: number | null;
  inputTokens: number | null;
  outputTokens: number | null;
  estimatedCostCents: number | null;
  errorCategory: string | null;
  errorMessage: string | null;
  traceId: string | null;
  spanId: string | null;
  requestId: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
};

export type AdminTelemetryEventsResponse = {
  summary: {
    total: number;
    returned: number;
    statusCounts: Record<string, number>;
    eventCounts: Record<string, number>;
  };
  events: AdminTelemetryEvent[];
  redaction: {
    detailPolicy: string;
  };
};

export type AdminTelemetryMetricsResponse = {
  summary: {
    totalEvents: number;
    failedEvents: number;
    completedEvents: number;
    runningEvents: number;
    averageLatencyMs: number | null;
  };
  runTypeCounts: Record<string, number>;
  providerCounts: Record<string, number>;
  statusCounts: Record<string, number>;
  eventCounts: Record<string, number>;
  failureCategoryCounts: Record<string, number>;
  extraction?: {
    summary: {
      totalRuns: number;
      completedRuns: number;
      failedRuns: number;
      activeRuns: number;
      totalSlides: number;
      totalBlocks: number;
      totalAssets: number;
      partialErrorCount: number;
      slidesWithPartialErrors: number;
    };
    statusCounts: Record<string, number>;
    runTypeCounts: Record<string, number>;
    extractorCounts: Record<string, number>;
    sourceFormatCounts: Record<string, number>;
    textSourceCounts: Record<string, number>;
    assetTypeCounts: Record<string, number>;
  };
};

export type AdminTelemetryFailuresResponse = {
  summary: {
    totalFailures: number;
    returned: number;
  };
  failures: AdminTelemetryEvent[];
  redaction: {
    detailPolicy: string;
  };
};

export type AdminTelemetryRunDetailResponse = {
  run: {
    runId: string;
    runType: string;
    workspaceId: string | null;
    deckId: string | null;
    userId: string | null;
    status: string | null;
    provider: string | null;
    model: string | null;
    eventCount: number;
    failureCount: number;
    startedAt: string;
    lastEventAt: string;
  };
  events: AdminTelemetryEvent[];
  redaction: {
    detailPolicy: string;
  };
};

export type AdminTelemetryObservabilityResponse = {
  otelEnabled: boolean;
  serviceName: string;
  exporterConfigured: boolean;
  sampleRate: number;
  mode: string;
  error: string | null;
};

export type AdminRegressionCase = {
  id: string;
  sourceEventId: string;
  workspaceId: string | null;
  deckId: string | null;
  userId: string | null;
  runId: string | null;
  runType: string;
  eventName: string;
  status: string;
  failureCategory: string | null;
  title: string;
  fixture: Record<string, unknown>;
  notes: string | null;
  createdByUserId: string | null;
  createdAt: string | null;
  updatedAt: string | null;
};

export type AdminAgentTeam = {
  key: string;
  name: string;
  purpose: string;
  status: string;
  observedRunCount: number;
  roles: Array<{
    key: string;
    name: string;
    responsibility: string;
    status: string;
  }>;
  handoffs: string[];
  runTypes: string[];
  recentRuns: AdminAgentRun[];
};

export type AdminAgentTeamsResponse = {
  summary: {
    teamCount: number;
    observedRuns: number;
    runningRuns: number;
    failedRuns: number;
  };
  teams: AdminAgentTeam[];
  runTypeCounts: Record<string, number>;
  statusCounts: Record<string, number>;
  principles: string[];
};

export type AdminDeckProcessing = {
  deck: {
    id: string;
    title: string;
    status: string;
    workflowStatus?: WorkflowJobStatus | null;
    audience: string;
    purpose: string;
    sourceType: string | null;
    declaredSlideCount: number | null;
    summary: string | null;
    createdAt: string | null;
    updatedAt: string | null;
    userId: string | null;
    userEmail: string | null;
    workspaceId: string | null;
    workspaceName: string | null;
  };
  sourceFile: {
    id: string;
    filename: string;
    originalFilename: string | null;
    fileRole: string;
    mimeType: string;
    fileExtension: string | null;
    storageProvider: string;
    size: number;
    pageCount: number | null;
    hasStoragePath: boolean;
    uploadedAt: string | null;
  } | null;
  counts: Record<string, number>;
  pipeline: Array<{
    key: string;
    label: string;
    status: string;
  }>;
  structurePreview: {
    slideLimit: number;
    itemLimit: number;
    warningCount: number;
    warnings: Array<{
      slideId: string;
      slideIndex: number;
      sourcePageNumber: number | null;
      title: string;
      message: string;
    }>;
    slides: Array<{
      id: string;
      slideIndex: number;
      sourcePageNumber: number | null;
      title: string;
      role: string;
      semanticSlideType: string | null;
      textPreview: string | null;
      blockCount: number;
      assetCount: number;
      blocks: Array<Record<string, unknown>>;
      assets: Array<Record<string, unknown>>;
    }>;
  };
  extractionRuns: Array<Record<string, unknown>>;
  analysisRuns: Array<Record<string, unknown>>;
  generationJobs: Array<Record<string, unknown>>;
  designVersions: Array<Record<string, unknown>>;
  artifacts: Array<Record<string, unknown>>;
  observability: {
    worker: {
      workerRequired: boolean;
      state: string;
      queueState: string | null;
      runId: string | null;
      workflowJobId?: string | null;
      workflowJobType?: WorkflowJobType | null;
      workflowJobStatus?: WorkflowJobStatus | null;
      queuedTooLong: boolean;
      heartbeatStale: boolean;
      staleReason: string | null;
      message: string | null;
      oldestQueuedAt: string | null;
      lastHeartbeatAt: string | null;
      queuedAgeSeconds: number | null;
      heartbeatAgeSeconds: number | null;
      queuePosition: number | null;
    };
    currentPhase: string | null;
    currentPhaseKey: string | null;
    queuePosition: number | null;
    lastError: string | null;
    artifactStatus: string;
    brandStatus: string;
    miniatureStatus: string;
    llmStatus: string;
    chatStatus: string;
    visualizerStatus: string;
    exportStatus: string;
  };
  redaction: {
    sensitiveFieldsRedacted: string[];
    detailPolicy: string;
  };
};

export type AdminDeckSlides = {
  deck: {
    id: string;
    title: string;
    status: string;
    audience: string;
    purpose: string;
    createdAt: string | null;
    updatedAt: string | null;
    userId: string | null;
    userEmail: string | null;
    workspaceId: string | null;
    workspaceName: string | null;
  };
  counts: Record<string, number>;
  designVersions: Array<Record<string, unknown>>;
  slides: Array<{
    id: string;
    slideIndex: number;
    slideNumber: number | null;
    title: string;
    role: string;
    semanticSlideType: string | null;
    summary: string | null;
    textPreview: string | null;
    blockCount: number;
    assetCount: number;
    blocks: Array<Record<string, unknown>>;
    assets: Array<Record<string, unknown>>;
    generatedSlides: Array<{
      id: string;
      designVersionId: string;
      generationJobId: string | null;
      sourceSlideId: string | null;
      slideNumber: number;
      title: string;
      status: string;
      validationStatus: string;
      previewImageUrl: string | null;
      renderSchema: Record<string, unknown>;
      renderSchemaSummary: Record<string, unknown>;
      designTokens: Record<string, string>;
      elementCount: number;
      codeVersionCount: number;
      elements: Array<Record<string, unknown>>;
      codeVersions: Array<Record<string, unknown>>;
      createdAt: string | null;
      updatedAt: string | null;
    }>;
  }>;
  orphanGeneratedSlides: Array<Record<string, unknown>>;
  redaction: {
    sensitiveFieldsRedacted: string[];
    detailPolicy: string;
  };
};

export type AdminElementsResponse = {
  elements: Array<{
    id: string;
    deckId: string;
    deckTitle: string | null;
    userId: string | null;
    userEmail: string | null;
    workspaceId: string | null;
    workspaceName: string | null;
    generatedSlideId: string;
    generatedSlideTitle: string | null;
    generatedSlideNumber: number | null;
    sourceSlideId: string | null;
    sourceSlideTitle: string | null;
    designVersionId: string;
    designVersionName: string | null;
    designVersionStatus: string | null;
    elementKey: string;
    elementType: string;
    parentElementId: string | null;
    zIndex: number;
    geometry: {
      x: number;
      y: number;
      width: number;
      height: number;
      rotation: number;
    };
    locked: boolean;
    visible: boolean;
    hasStylePayload: boolean;
    hasContentPayload: boolean;
    styleKeys: string[];
    contentKeys: string[];
    versionCount: number;
    variationJobCount: number;
    versions: Array<Record<string, unknown>>;
    variationJobs: Array<Record<string, unknown>>;
    createdAt: string | null;
    updatedAt: string | null;
  }>;
  total: number;
  limit: number;
  filters: {
    deckId: string | null;
  };
  typeCounts: Record<string, number>;
  versionStatusCounts: Record<string, number>;
  redaction: {
    sensitiveFieldsRedacted: string[];
    detailPolicy: string;
  };
};

export type AdminQuotasResponse = {
  summary: {
    aiUsageBucketCount: number;
    rateLimitBucketCount: number;
    dailyAiGenerationQuota: number;
    aiBucketsReturned: number;
    rateBucketsReturned: number;
  };
  aiUsageBuckets: Array<Record<string, unknown>>;
  rateLimitBuckets: Array<Record<string, unknown>>;
  recentFailures: Array<Record<string, unknown>>;
  redaction: {
    sensitiveFieldsRedacted: string[];
    detailPolicy: string;
  };
};

export type AdminProviderHealthResponse = {
  summary: {
    workspacesReturned: number;
    workspaceCount: number;
    configured: number;
    skipped: number;
    missing: number;
    revoked: number;
    systemAnthropicConfigured: boolean;
    systemOpenAiConfigured: boolean;
    generationMode: string;
    mockMode: boolean;
    uploadStorageBackend: string;
    uploadStorageS3Configured: boolean;
    uploadStorageS3BucketConfigured: boolean;
    uploadStorageS3RegionConfigured: boolean;
  };
  providerCounts: Record<string, number>;
  workspaces: Array<Record<string, unknown>>;
  recentFailures: Array<Record<string, unknown>>;
  redaction: {
    sensitiveFieldsRedacted: string[];
    detailPolicy: string;
  };
};

export type AdminDeploymentReadinessCheck = {
  status: string;
  ok: boolean;
  message: string;
  details: Record<string, unknown> | null;
};

export type AdminDeploymentReadinessResponse = {
  ok: boolean;
  status: string;
  environment: string;
  serviceRole: string;
  checkedAt: string;
  checks: Record<string, AdminDeploymentReadinessCheck>;
  summary: {
    hardOk: boolean;
    warningCount: number;
    failedCount: number;
    readyForTesterTraffic: boolean;
    nextDeploymentCheckAt: string;
  };
};

export type AdminAuditResponse = {
  events: Array<{
    id: string;
    actorUserId: string | null;
    actorEmail: string | null;
    action: string;
    resourceType: string | null;
    resourceId: string | null;
    result: string;
    requestId: string | null;
    hasSourceIp: boolean;
    hasUserAgent: boolean;
    detailKeys: string[];
    createdAt: string | null;
  }>;
  total: number;
  limit: number;
  filters: {
    action: string | null;
    result: string | null;
    resourceType: string | null;
    actor: string | null;
  };
  resultCounts: Record<string, number>;
  resourceTypeCounts: Record<string, number>;
  topActions: Array<{ action: string; count: number }>;
  redaction: {
    sensitiveFieldsRedacted: string[];
    detailPolicy: string;
  };
};

export type AdminFailureTicket = {
  id: string;
  route: string | null;
  pageUrl: string | null;
  apiPath: string | null;
  statusCode: number | null;
  userId: string | null;
  userEmail: string | null;
  deckId: string | null;
  errorName: string | null;
  errorMessage: string | null;
  hasStack: boolean;
  contextKeys: string[];
  severity: string;
  source: string;
  status: string;
  requestId: string | null;
  adminNotes: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  acknowledgedAt: string | null;
  fixedAt: string | null;
  ignoredAt: string | null;
};

export type AdminFailureTicketDetail = {
  ticket: AdminFailureTicket & {
    errorStack: string | null;
    context: Record<string, unknown>;
  };
  redaction: {
    detailPolicy: string;
  };
};

export type AdminFailureTicketsResponse = {
  tickets: AdminFailureTicket[];
  total: number;
  limit: number;
  filters: {
    status: string | null;
    severity: string | null;
    source: string | null;
    deckId: string | null;
  };
  statusCounts: Record<string, number>;
  severityCounts: Record<string, number>;
  sourceCounts: Record<string, number>;
  redaction: {
    sensitiveFieldsRedacted: string[];
    detailPolicy: string;
  };
};

export type AdminSafetyGuardrailDecision = {
  id: string;
  action: string;
  result: string;
  resourceType: string | null;
  resourceId: string | null;
  requestId: string | null;
  actorEmail: string | null;
  createdAt: string;
  allowed: boolean;
  riskLevel: string | null;
  reason: string | null;
  policy: string | null;
  blockedReasons: string[];
};

export type AdminSafetyControls = {
  summary: {
    incidentBacklogTotal: number;
    incidentBacklogNew: number;
    incidentBacklogCritical: number;
    guardrailBlockedTickets: number;
    guardrailEvaluations: number;
    guardrailsConfigured: boolean;
    guardrailStatus: string | null;
    superAdminConfigured: boolean;
    superAdminStatus: string | null;
  };
  guardrails: {
    configured: boolean;
    status: string;
    health: Record<string, unknown> | null;
    operatorSummary: Record<string, unknown> | null;
    policyRegistry: Record<string, unknown> | null;
    audits: Record<string, unknown>[];
    error: string | null;
    baseUrl: string | null;
  };
  superAdminService: {
    configured: boolean;
    status: string;
    health: Record<string, unknown> | null;
    error: string | null;
    baseUrl: string | null;
  };
  guardrailDecisions: {
    counts: {
      allowed: number;
      blocked: number;
      failed: number;
    };
    events: AdminSafetyGuardrailDecision[];
    operatorSummary: Record<string, unknown> | null;
  };
  incidentBacklog: {
    total: number;
    new: number;
    critical: number;
    tickets: Array<{
      id: string;
      status: string;
      severity: string;
      source: string;
      route: string | null;
      apiPath: string | null;
      userEmail: string | null;
      deckId: string | null;
      errorName: string | null;
      errorMessage: string | null;
      createdAt: string | null;
      requestId: string | null;
      statusCode: number | null;
    }>;
  };
  redaction: {
    sensitiveFieldsRedacted: string[];
    detailPolicy: string;
  };
};
