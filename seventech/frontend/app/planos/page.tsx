'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/app/components/ui/card';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Label } from '@/app/components/ui/label';
import { Badge } from '@/app/components/ui/badge';
import { Alert, AlertDescription } from '@/app/components/ui/alert';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/app/components/ui/alert-dialog';
import { toast } from 'sonner';
import { 
  Play, 
  RefreshCw, 
  Plus, 
  Search, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  FileText,
  Settings,
  ExternalLink
} from 'lucide-react';
import AppHeader from '@/app/components/AppHeader';
import NewMappingModal from './NewMappingModal';
import ViewStepsModal from './ViewStepsModal';
import ViewExecutionModal from './ViewExecutionModal';
import { plansApi, executionApi } from '@/app/services/api';
import { Plan, ExecutionResult } from '@/app/services/types';
import { formatDuration } from '@/app/utils/utils';

export default function PlanosPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [executionParams, setExecutionParams] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isNewMappingModalOpen, setIsNewMappingModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isViewStepsModalOpen, setIsViewStepsModalOpen] = useState(false);
  const [isViewExecutionModalOpen, setIsViewExecutionModalOpen] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<ExecutionResult | null>(null);
  const [executions, setExecutions] = useState<ExecutionResult[]>([]);

  // Load plans on component mount
  useEffect(() => {
    loadPlans();
  }, []);

  // Reset execution params when plan changes
  useEffect(() => {
    if (selectedPlan) {
      const initialParams: Record<string, string> = {};
      selectedPlan.metadata.required_params.forEach(param => {
        initialParams[param] = '';
      });
      setExecutionParams(initialParams);
      setExecutionResult(null);
      setError(null);
      loadExecutions(selectedPlan.metadata.plan_id);
    }
  }, [selectedPlan]);

  const loadPlans = async () => {
    setIsLoading(true);
    try {
      const plansData = await plansApi.getAll();
      setPlans(plansData);
      if (plansData.length > 0 && !selectedPlan) {
        setSelectedPlan(plansData[0]);
      }
    } catch (err) {
      setError('Erro ao carregar planos: ' + (err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadExecutions = async (planId: string) => {
    try {
      const executionsData = await executionApi.getAll(planId);
      setExecutions(executionsData);
    } catch (err) {
      console.error('Erro ao carregar execuções:', err);
      setExecutions([]);
    }
  };

  const handleExecutePlan = async () => {
    if (!selectedPlan) return;

    setIsExecuting(true);
    setError(null);
    try {
      const result = await executionApi.execute(selectedPlan.metadata.plan_id, executionParams);
      setExecutionResult(result);
    } catch (err) {
      setError('Erro na execução: ' + (err as Error).message);
    } finally {
      setIsExecuting(false);
    }
  };

  const handlePlanCreated = (newPlan: Plan) => {
    setPlans(prev => [newPlan, ...prev]);
    setSelectedPlan(newPlan);
    // Don't close modal automatically - let user click "Concluir"
  };

  const handleDeletePlan = async () => {
    if (!selectedPlan) return;

    setIsLoading(true);
    try {
      await plansApi.delete(selectedPlan.metadata.plan_id);
      
      // Remove plan from list
      setPlans(prev => prev.filter(plan => plan.metadata.plan_id !== selectedPlan.metadata.plan_id));
      
      // Select next plan or clear selection
      const currentIndex = plans.findIndex(plan => plan.metadata.plan_id === selectedPlan.metadata.plan_id);
      const remainingPlans = plans.filter(plan => plan.metadata.plan_id !== selectedPlan.metadata.plan_id);
      
      if (remainingPlans.length > 0) {
        const nextIndex = currentIndex < remainingPlans.length ? currentIndex : remainingPlans.length - 1;
        setSelectedPlan(remainingPlans[nextIndex]);
      } else {
        setSelectedPlan(null);
      }

      toast.success('Plano excluído com sucesso');
      setIsDeleteDialogOpen(false);
    } catch (err) {
      toast.error('Erro ao excluir plano: ' + (err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewExecution = (execution: ExecutionResult) => {
    setSelectedExecution(execution);
    setIsViewExecutionModalOpen(true);
  };

  const filteredPlans = plans.filter(plan => 
    plan.metadata.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    plan.metadata.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    plan.metadata.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failure':
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'timeout':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-blue-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      success: 'bg-green-100 text-green-800 border-green-200',
      failure: 'bg-red-100 text-red-800 border-red-200',
      error: 'bg-red-100 text-red-800 border-red-200',
      timeout: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      partial_success: 'bg-orange-100 text-orange-800 border-orange-200'
    };
    
    return (
      <Badge className={variants[status] || 'bg-gray-100 text-gray-800 border-gray-200'}>
        {getStatusIcon(status)}
        <span className="ml-1">{status}</span>
      </Badge>
    );
  };

  return (
    <>
      <div className="flex justify-center px-4">
        <div className="w-full max-w-7xl">
          <AppHeader 
            title="Gerenciador de Planos" 
            subtitle="Execute automações criadas com mapeamento interativo"
          />
        </div>
      </div>
      
      <div className="flex justify-center px-4 pb-6">
        <div className="w-full max-w-7xl">
          <div className="grid gap-6 lg:grid-cols-3 h-[calc(100vh-200px)]">
            
            {/* Left Panel - Plans List */}
            <div className="flex flex-col h-full">
              <Card className="flex flex-col h-full">
                <CardHeader className="pb-3 flex-shrink-0">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Planos | {filteredPlans.length} {filteredPlans.length === 1 ? 'serviço disponível' : 'serviços disponíveis'}</CardTitle>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => setIsNewMappingModalOpen(true)}>
                        <Plus className="h-4 w-4 mr-1" />
                        Novo
                      </Button>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Search className="h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Buscar planos..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="text-sm"
                    />
                  </div>
                </CardHeader>
                <CardContent className="p-0 flex-1 overflow-hidden">
                  <div className="h-full overflow-y-auto">
                    {filteredPlans.map((plan) => (
                      <div
                        key={plan.metadata.plan_id}
                        onClick={() => setSelectedPlan(plan)}
                        className={`p-4 cursor-pointer border-l-4 transition-all border-b ${
                          selectedPlan?.metadata.plan_id === plan.metadata.plan_id
                            ? 'border-l-primary bg-primary/5 shadow-sm'
                            : 'border-l-transparent hover:border-l-primary/50 hover:bg-muted/50'
                        }`}
                      >
                        <div className="space-y-2">
                          <div className="flex items-start justify-between">
                            <h3 className="font-medium text-sm leading-tight">{plan.metadata.name}</h3>
                          </div>
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {plan.metadata.description}
                          </p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span>{plan.steps.length} etapas</span>
                            {plan.metadata.required_params.length > 0 && (
                              <>
                                <span>•</span>
                                <span>{plan.metadata.required_params.length} parâmetros</span>
                              </>
                            )}
                          </div>
                          {plan.metadata.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {plan.metadata.tags.slice(0, 3).map((tag, index) => (
                                <Badge key={index} variant="secondary" className="text-xs px-1 py-0">
                                  {tag}
                                </Badge>
                              ))}
                              {plan.metadata.tags.length > 3 && (
                                <Badge variant="secondary" className="text-xs px-1 py-0">
                                  +{plan.metadata.tags.length - 3}
                                </Badge>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    
                    {filteredPlans.length === 0 && !isLoading && (
                      <div className="p-8 text-center">
                        <FileText className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                        <p className="text-sm text-muted-foreground">
                          {searchQuery ? 'Nenhum plano encontrado' : 'Nenhum plano disponível'}
                        </p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right Panel - Plan Details & Execution */}
            <div className="lg:col-span-2 flex flex-col h-full">
              {selectedPlan ? (
                <Card className="flex flex-col h-full">
                  <CardHeader className="pb-3 flex-shrink-0">
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-xl">Detalhes do Plano</CardTitle>
                        <CardDescription className="mt-1">
                          {selectedPlan.metadata.name}
                        </CardDescription>
                      </div>
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => setIsViewStepsModalOpen(true)}
                        >
                          <FileText className="h-4 w-4 mr-1" />
                          Ver Steps
                        </Button>
                        <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
                          <AlertDialogTrigger asChild>
                            <Button 
                              variant="destructive" 
                              size="sm"
                              disabled={isLoading}
                            >
                              Excluir
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Excluir Plano</AlertDialogTitle>
                              <AlertDialogDescription>
                                Tem certeza que deseja excluir o plano &quot;{selectedPlan?.metadata.name}&quot;? 
                                Esta ação não pode ser desfeita e todos os dados relacionados serão perdidos.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel disabled={isLoading}>Cancelar</AlertDialogCancel>
                              <AlertDialogAction 
                                onClick={handleDeletePlan}
                                disabled={isLoading}
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              >
                                {isLoading ? (
                                  <>
                                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                                    Excluindo...
                                  </>
                                ) : (
                                  'Excluir'
                                )}
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="flex-1 overflow-y-auto">
                    <div className="space-y-6">

                      {/* Basic Info Section */}
                      <div>
                        <h3 className="text-sm font-medium text-muted-foreground mb-3">📊 Informações Básicas</h3>
                        <div className="grid gap-4 md:grid-cols-2">
                          <div>
                            <Label className="text-sm font-medium text-muted-foreground">ID do Plano:</Label>
                            <p className="font-mono text-sm">{selectedPlan.metadata.plan_id}</p>
                          </div>
                          {selectedPlan.metadata.created_at && (
                            <div>
                              <Label className="text-sm font-medium text-muted-foreground">Created at:</Label>
                              <p className="font-semibold">{new Date(selectedPlan.metadata.created_at).toLocaleString('pt-BR')}</p>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* URL */}
                      {selectedPlan.metadata.url && (
                        <div>
                          <h3 className="text-sm font-medium text-muted-foreground mb-3">🔗 URL</h3>
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-mono bg-muted px-3 py-2 rounded flex-1 border">
                              {selectedPlan.metadata.url}
                            </p>
                            <Button variant="ghost" size="sm">
                              <ExternalLink className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* Expected Output */}
                      {selectedPlan.metadata.expected_output && (
                        <div>
                          <h3 className="text-sm font-medium text-muted-foreground mb-3">🎯 Expected output</h3>
                          <p className="text-sm bg-muted px-3 py-2 rounded border">
                            {selectedPlan.metadata.expected_output}
                          </p>
                        </div>
                      )}

                      {/* Tags */}
                      {selectedPlan.metadata.tags.length > 0 && (
                        <div>
                          <h3 className="text-sm font-medium text-muted-foreground mb-3">🏷️ Tags</h3>
                          <div className="flex flex-wrap gap-1">
                            {selectedPlan.metadata.tags.map((tag, index) => (
                              <Badge key={index} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Separator */}
                      <hr className="border-border" />

                      {/* Schema */}
                      <div>
                        <h3 className="text-sm font-medium text-muted-foreground mb-3">📋 Esquema do Plano</h3>
                        
                        {/* Execution Form */}
                        <div className="border rounded-lg p-4 bg-muted/30">
                          <div className="mb-4">
                            <h4 className="text-lg font-semibold">Formulário de Execução</h4>
                            <p className="text-sm text-muted-foreground">
                              {selectedPlan.metadata.description}
                            </p>
                          </div>

                          <div className="space-y-4">
                            {/* Required Parameters */}
                            {selectedPlan.metadata.required_params.map((param) => (
                              <div key={param} className="space-y-2">
                                <Label htmlFor={param} className="text-sm font-medium">
                                  {param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} *
                                </Label>
                                <Input
                                  id={param}
                                  value={executionParams[param] || ''}
                                  onChange={(e) => setExecutionParams(prev => ({
                                    ...prev,
                                    [param]: e.target.value
                                  }))}
                                  placeholder={`Digite ${param.replace(/_/g, ' ')}`}
                                  className="w-full"
                                />
                              </div>
                            ))}

                            {/* Execute Button */}
                            <div className="pt-4">
                              <Button 
                                onClick={handleExecutePlan}
                                disabled={isExecuting || selectedPlan.metadata.required_params.some(param => !executionParams[param])}
                                className="w-full"
                                size="lg"
                              >
                                {isExecuting ? (
                                  <>
                                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                                    Executando...
                                  </>
                                ) : (
                                  <>
                                    <Play className="mr-2 h-4 w-4" />
                                    Executar Plano
                                  </>
                                )}
                              </Button>
                            </div>

                            {/* Error Display */}
                            {error && (
                              <Alert className="border-destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{error}</AlertDescription>
                              </Alert>
                            )}

                            {/* Execution Result */}
                            {executionResult && (
                              <div className="border-t pt-4 mt-4">
                                <div className="flex items-center justify-between mb-4">
                                  <h3 className="text-lg font-semibold">Resultado da Execução</h3>
                                  {getStatusBadge(executionResult.status)}
                                </div>
                                
                                <div className="space-y-3">
                                  <div className="grid gap-4 md:grid-cols-2">
                                    <div>
                                      <Label className="text-sm font-medium text-muted-foreground">Etapas Completadas</Label>
                                      <p className="font-semibold">{executionResult.steps_completed}/{executionResult.total_steps}</p>
                                    </div>
                                    {executionResult.execution_time_ms && (
                                      <div>
                                        <Label className="text-sm font-medium text-muted-foreground">Tempo de Execução</Label>
                                        <p className="font-semibold">{executionResult.execution_time_ms}ms</p>
                                      </div>
                                    )}
                                  </div>

                                  {/* Artifacts */}
                                  {executionResult.artifacts.length > 0 && (
                                    <div>
                                      <Label className="text-sm font-medium text-muted-foreground">Artefatos Gerados</Label>
                                      <div className="space-y-2 mt-2">
                                        {executionResult.artifacts.map((artifact, index) => (
                                          <div key={index} className="flex items-center gap-2 p-2 bg-muted rounded">
                                            <FileText className="h-4 w-4" />
                                            <span className="text-sm">{artifact.name}</span>
                                            <Badge variant="outline" className="text-xs">
                                              {artifact.type}
                                            </Badge>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {/* Error Message */}
                                  {executionResult.error_message && (
                                    <div>
                                      <Label className="text-sm font-medium text-muted-foreground">Erro</Label>
                                      <p className="text-sm text-red-600 mt-1">{executionResult.error_message}</p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Separator */}
                      <hr className="border-border" />

                      {/* Executions Section */}
                      <div>
                        <h3 className="text-sm font-medium text-muted-foreground mb-3">📈 Histórico de Execuções</h3>
                        <div className="h-64 overflow-y-auto border rounded-lg bg-muted/30">
                          {executions.length > 0 ? (
                            <div className="space-y-2 p-3">
                              {executions.map((execution, index) => (
                                <div
                                  key={execution.execution_id}
                                  onClick={() => handleViewExecution(execution)}
                                  className="p-3 bg-background rounded border cursor-pointer hover:bg-accent/50 transition-colors"
                                >
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                      <Badge variant="outline" className="text-xs font-mono shrink-0">
                                        #{index + 1}
                                      </Badge>
                                      {getStatusIcon(execution.status)}
                                      <span className="text-sm font-medium">
                                        {execution.execution_id.slice(0, 8)}...
                                      </span>
                                    </div>
                                    {getStatusBadge(execution.status)}
                                  </div>
                                  <div className="mt-1 text-xs text-muted-foreground">
                                    {execution.steps_completed}/{execution.total_steps} etapas
                                    {execution.execution_time_ms && (
                                      <span className="ml-2">• {formatDuration(execution.execution_time_ms)}</span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                              Nenhuma execução encontrada
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card className="flex flex-col h-full">
                  <CardContent className="flex items-center justify-center flex-1">
                    <div className="text-center">
                      <Settings className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-muted-foreground">Selecione um plano para ver os detalhes</p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* View Steps Modal */}
      <ViewStepsModal
        isOpen={isViewStepsModalOpen}
        onClose={() => setIsViewStepsModalOpen(false)}
        plan={selectedPlan}
      />

      {/* View Execution Modal */}
      <ViewExecutionModal
        isOpen={isViewExecutionModalOpen}
        onClose={() => setIsViewExecutionModalOpen(false)}
        execution={selectedExecution}
      />

      {/* New Mapping Modal */}
      <NewMappingModal
        isOpen={isNewMappingModalOpen}
        onClose={() => setIsNewMappingModalOpen(false)}
        onPlanCreated={handlePlanCreated}
      />
    </>
  );
}