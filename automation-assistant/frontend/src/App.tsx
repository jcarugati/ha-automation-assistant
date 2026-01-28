import { useState, useEffect, useMemo, useCallback } from 'react'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Sidebar, MainContent, type ViewType } from '@/components/layout'
import { WelcomeView, CreateView, DetailView, InsightsView } from '@/components/views'
import { DeployModal, ScheduleModal, DeleteModal } from '@/components/modals'
import { useAutomations, useInsights, useFilters, useSchedule } from '@/hooks'
import { getVersion, runBatchDiagnosis } from '@/api'
import type { Insight } from '@/types'

export default function App() {
  const [version, setVersion] = useState('')
  const [currentView, setCurrentView] = useState<ViewType>('welcome')
  const [diagnosisRunning, setDiagnosisRunning] = useState(false)

  // Modal state
  const [deployModalOpen, setDeployModalOpen] = useState(false)
  const [deployYaml, setDeployYaml] = useState('')
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)

  // Messages
  const [globalError, setGlobalError] = useState<string | null>(null)
  const [globalSuccess, setGlobalSuccess] = useState<string | null>(null)

  // Hooks
  const {
    automations,
    loading: automationsLoading,
    current: currentAutomation,
    currentLoading,
    refresh: refreshAutomations,
    selectAutomation,
    clearCurrent,
  } = useAutomations()

  const {
    insights,
    automationIdsWithIssues,
    getIssuesForAutomation,
    getSeverityForAutomation,
    refresh: refreshInsights,
    resolveInsight,
    unresolvedCount,
  } = useInsights()

  const {
    searchQuery,
    setSearchQuery,
    filter,
    setFilter,
    groupBy,
    setGroupBy,
    filterAutomations,
    groupAutomations,
  } = useFilters()

  const { schedule, updateSchedule } = useSchedule()

  // Load version on mount
  useEffect(() => {
    async function loadVersion() {
      try {
        const data = await getVersion()
        setVersion(data.version)
      } catch (e) {
        console.warn('Failed to load version:', e)
      }
    }
    void loadVersion()
  }, [])

  // Compute filtered and grouped automations
  const filteredAutomations = useMemo(
    () => filterAutomations(automations, automationIdsWithIssues),
    [automations, automationIdsWithIssues, filterAutomations]
  )

  const groups = useMemo(
    () => groupAutomations(filteredAutomations),
    [filteredAutomations, groupAutomations]
  )

  // View handlers
  const handleViewChange = useCallback(
    (view: ViewType) => {
      setCurrentView(view)
      if (view !== 'detail') {
        clearCurrent()
      }
    },
    [clearCurrent]
  )

  const handleAutomationSelect = useCallback(
    async (id: string) => {
      await selectAutomation(id)
      setCurrentView('detail')
    },
    [selectAutomation]
  )

  // Diagnosis
  const handleRunDiagnosis = useCallback(async () => {
    setDiagnosisRunning(true)
    try {
      await runBatchDiagnosis()
      await refreshInsights()
      await refreshAutomations()
      setCurrentView('insights')
    } catch (e) {
      console.error('Batch diagnosis failed:', e)
    } finally {
      setDiagnosisRunning(false)
    }
  }, [refreshInsights, refreshAutomations])

  // Deploy modal
  const handleOpenDeployModal = useCallback((yaml: string) => {
    setDeployYaml(yaml)
    setDeployModalOpen(true)
  }, [])

  // Schedule modal
  const handleSaveSchedule = useCallback(
    async (request: {
      enabled: boolean
      time: string
      frequency: 'daily' | 'weekly' | 'monthly'
      day_of_week: string
      day_of_month: number
    }) => {
      await updateSchedule(request)
    },
    [updateSchedule]
  )

  // Delete handler
  const handleDelete = useCallback(() => {
    setGlobalError('Delete not implemented - remove automation from HA directly')
    setDeleteModalOpen(false)
  }, [])

  // Insight actions
  const handleGetFix = useCallback((insightId: string) => {
    // TODO: Implement AI fix modal
    alert('AI fix generation - coming soon')
    console.log('Get fix for:', insightId)
  }, [])

  // Current automation issues
  const currentIssues: Insight[] = currentAutomation
    ? getIssuesForAutomation(currentAutomation.automation.id)
    : []

  // All insights for InsightsView
  const allInsights = [...insights.single_automation, ...insights.multi_automation]

  return (
    <TooltipProvider>
      <div className="flex h-screen bg-background text-foreground">
        <Sidebar
          version={version}
          currentView={currentView}
          onViewChange={handleViewChange}
          automations={automations}
          automationsLoading={automationsLoading}
          selectedAutomationId={currentAutomation?.automation.id ?? null}
          onAutomationSelect={(id) => void handleAutomationSelect(id)}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          filter={filter}
          onFilterChange={setFilter}
          groupBy={groupBy}
          onGroupByChange={setGroupBy}
          groups={groups}
          getSeverity={getSeverityForAutomation}
          unresolvedInsightsCount={unresolvedCount}
        />

        <MainContent>
          {globalError && (
            <div className="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm border border-destructive/30">
              {globalError}
            </div>
          )}
          {globalSuccess && (
            <div className="mb-4 p-3 rounded-lg bg-success/10 text-success text-sm border border-success/30">
              {globalSuccess}
            </div>
          )}

          {currentView === 'welcome' && (
            <WelcomeView
              automations={automations}
              automationIdsWithIssues={automationIdsWithIssues}
              schedule={schedule}
              onCreateClick={() => {
                handleViewChange('create')
              }}
              onInsightsClick={() => {
                handleViewChange('insights')
              }}
              onRunDiagnosis={() => void handleRunDiagnosis()}
              onScheduleClick={() => {
                setScheduleModalOpen(true)
              }}
              diagnosisRunning={diagnosisRunning}
            />
          )}

          {currentView === 'create' && <CreateView onDeployClick={handleOpenDeployModal} />}

          {currentView === 'detail' && currentAutomation && (
            <DetailView
              details={currentAutomation}
              detailsLoading={currentLoading}
              issues={currentIssues}
              onRefresh={async () => {
                await refreshAutomations()
                await selectAutomation(currentAutomation.automation.id)
              }}
              onDelete={() => {
                setDeleteModalOpen(true)
              }}
            />
          )}

          {currentView === 'insights' && (
            <InsightsView
              insights={allInsights}
              onRunDiagnosis={() => void handleRunDiagnosis()}
              diagnosisRunning={diagnosisRunning}
              onViewAutomation={(id) => void handleAutomationSelect(id)}
              onResolveInsight={(insightId, resolved) => void resolveInsight(insightId, resolved)}
              onGetFix={(insightId) => {
                handleGetFix(insightId)
              }}
            />
          )}
        </MainContent>

        <DeployModal
          open={deployModalOpen}
          onOpenChange={setDeployModalOpen}
          yaml={deployYaml}
          onSuccess={(message) => {
            setGlobalSuccess(message)
            void refreshAutomations()
            setTimeout(() => {
              setGlobalSuccess(null)
            }, 5000)
          }}
          onError={(message) => {
            setGlobalError(message)
            setTimeout(() => {
              setGlobalError(null)
            }, 5000)
          }}
        />

        <ScheduleModal
          open={scheduleModalOpen}
          onOpenChange={setScheduleModalOpen}
          schedule={schedule}
          onSave={handleSaveSchedule}
        />

        <DeleteModal
          open={deleteModalOpen}
          onOpenChange={setDeleteModalOpen}
          automationName={currentAutomation?.automation.alias ?? ''}
          onConfirm={handleDelete}
        />
      </div>
    </TooltipProvider>
  )
}
