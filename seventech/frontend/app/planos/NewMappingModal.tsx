'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Label } from '@/app/components/ui/label';
import { Badge } from '@/app/components/ui/badge';
import { Alert, AlertDescription } from '@/app/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/app/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/app/components/ui/dialog';
import {
  Play,
  RefreshCw,
  X,
  AlertCircle,
  CheckCircle,
  Clock,
  Globe,
  Tag,
  FileText,
  Send,
  MapPin
} from 'lucide-react';
import { mappingApi } from '@/app/services/api';
import { MappingSession, StartMappingRequest, Plan } from '@/app/services/types';

interface NewMappingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPlanCreated: (plan: Plan) => void;
}

export default function NewMappingModal({ isOpen, onClose, onPlanCreated }: NewMappingModalProps) {
  const [step, setStep] = useState<'form' | 'mapping' | 'completed'>('form');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form state
  const [objective, setObjective] = useState('pegar o valor do iptu no site https://iportal.rio.rj.gov.br/PF331IPTUATUAL/');
  const [startingUrl, setStartingUrl] = useState('https://iportal.rio.rj.gov.br/PF331IPTUATUAL/');
  const [tags, setTags] = useState<string[]>(['iptu']);
  const [tagInput, setTagInput] = useState('');
  const [planName, setPlanName] = useState('Pegar valor do IPTU Rio');
  
  // Mapping state
  const [session, setSession] = useState<MappingSession | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [isSubmittingInput, setIsSubmittingInput] = useState(false);
  const [createdPlan, setCreatedPlan] = useState<Plan | null>(null);
  
  // SSE connection
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const resetForm = () => {
    setStep('form');
    setObjective('pegar o valor do iptu no site https://iportal.rio.rj.gov.br/PF331IPTUATUAL/');
    setStartingUrl('https://iportal.rio.rj.gov.br/PF331IPTUATUAL/');
    setTags(['iptu']);
    setTagInput('');
    setPlanName('Pegar valor do IPTU Rio');
    setSession(null);
    setInputValue('');
    setCreatedPlan(null);
    setError(null);
    setIsLoading(false);
    setIsSubmittingInput(false);
  };

  const handleClose = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    resetForm();
    onClose();
  };

  const addTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleKeyPress = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      action();
    }
  };

  const startMapping = async () => {
    if (!objective.trim()) {
      setError('Objetivo é obrigatório');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      const request: StartMappingRequest = {
        objective: objective.trim(),
        starting_url: startingUrl.trim() || undefined,
        tags: tags,
        plan_name: planName.trim() || undefined,
      };

      const response = await mappingApi.start(request);
      const sessionId = response.session_id; // Store session ID for use in callbacks
      
      setStep('mapping');
      
      // Start SSE connection - Remove leading slash from sse_url if present
      const sseUrl = response.sse_url.startsWith('/') ? response.sse_url.substring(1) : response.sse_url;
      const fullSseUrl = `${'http://localhost:8000'}/${sseUrl}`;
      
      console.log('Connecting to SSE:', fullSseUrl);
      
      const eventSource = new EventSource(fullSseUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE Connection opened');
      };

      eventSource.onmessage = (event) => {
        console.log('SSE Message:', event.data);
      };

      eventSource.addEventListener('status_change', (event) => {
        try {
          const sessionData = JSON.parse(event.data) as MappingSession;
          setSession(sessionData);
          console.log('Status changed:', sessionData.status);
        } catch (e) {
          console.error('Error parsing status_change event:', e);
        }
      });

      eventSource.addEventListener('input_needed', (event) => {
        try {
          const sessionData = JSON.parse(event.data) as MappingSession;
          setSession(sessionData);
          console.log('Input needed:', sessionData.current_input_request);
        } catch (e) {
          console.error('Error parsing input_needed event:', e);
        }
      });

      eventSource.addEventListener('completed', (event) => {
        try {
          const sessionData = JSON.parse(event.data) as MappingSession;
          setSession(sessionData);
          setStep('completed');
          console.log('Mapping completed');
          
          // Close SSE connection and polling after completion
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
          }
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
        } catch (e) {
          console.error('Error parsing completed event:', e);
        }
      });

      eventSource.addEventListener('failed', (event) => {
        try {
          const sessionData = JSON.parse(event.data) as MappingSession;
          setSession(sessionData);
          setError('Mapeamento falhou');
          console.log('Mapping failed');
        } catch (e) {
          console.error('Error parsing failed event:', e);
        }
      });

      eventSource.onerror = (error) => {
        console.log('SSE ReadyState:', eventSource.readyState);
        
        // Don't show error if connection was intentionally closed
        if (eventSourceRef.current === null) {
          console.log('SSE connection closed after completion');
          return;
        }
        
        // Check if this is a completion-related closure by polling session status
        if (eventSource.readyState === EventSource.CLOSED) {
          // Poll the session to check if it completed
          setTimeout(async () => {
            try {
              const sessionData = await mappingApi.getSession(sessionId);
              if (sessionData.status === 'completed') {
                console.log('Session completed, transitioning to completed step');
                setSession(sessionData);
                setStep('completed');
                if (eventSourceRef.current) {
                  eventSourceRef.current.close();
                  eventSourceRef.current = null;
                }
                return;
              }
            } catch (err) {
              console.error('Error checking session status:', err);
            }
            
            // If we get here, it's a real error
            console.error('SSE Error:', error);
            setError('Conexão SSE foi fechada pelo servidor');
          }, 1000);
        } else if (eventSource.readyState === EventSource.CONNECTING) {
          console.log('SSE tentando reconectar...');
        } else {
          console.error('SSE Error:', error);
          setError('Erro na conexão com o servidor de eventos');
        }
      };

      // Initial session fetch
      try {
        const initialSession = await mappingApi.getSession(sessionId);
        setSession(initialSession);
      } catch (sessionErr) {
        console.error('Error fetching initial session:', sessionErr);
        // Continue with SSE connection anyway
      }

      // Backup polling to check session status (in case SSE events are missed)
      const pollInterval = setInterval(async () => {
        try {
          const currentSession = await mappingApi.getSession(sessionId);
          setSession(currentSession);
          
          if (currentSession.status === 'completed') {
            console.log('Session completed via polling, transitioning to completed step');
            setStep('completed');
            clearInterval(pollInterval);
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
          } else if (currentSession.status === 'failed' || currentSession.status === 'cancelled') {
            console.log('Session failed/cancelled via polling');
            setError('Mapeamento falhou');
            clearInterval(pollInterval);
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
          }
        } catch (pollErr) {
          console.error('Polling error:', pollErr);
        }
      }, 2000); // Poll every 2 seconds

      // Store interval ref for cleanup
      pollIntervalRef.current = pollInterval;

    } catch (err) {
      setError('Erro ao iniciar mapeamento: ' + (err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const submitInput = async () => {
    if (!session || !inputValue.trim()) return;

    setIsSubmittingInput(true);
    try {
      await mappingApi.provideInput(session.session_id, { value: inputValue.trim() });
      setInputValue('');
    } catch (err) {
      setError('Erro ao enviar entrada: ' + (err as Error).message);
    } finally {
      setIsSubmittingInput(false);
    }
  };

  const createPlan = async () => {
    if (!session) return;

    setIsLoading(true);
    try {
      const plan = await mappingApi.createPlan(session.session_id, planName.trim() || undefined);
      setCreatedPlan(plan);
      onPlanCreated(plan);
      // Modal stays open to show success message, will close only when user clicks "Concluir"
    } catch (err) {
      setError('Erro ao criar plano: ' + (err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompleteAndClose = () => {
    handleClose();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-success" />;
      case 'failed':
      case 'cancelled':
        return <X className="h-4 w-4 text-destructive" />;
      case 'running':
        return <RefreshCw className="h-4 w-4 text-primary animate-spin" />;
      case 'waiting_for_input':
        return <Clock className="h-4 w-4 text-warning" />;
      default:
        return <MapPin className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-success/10 text-success border-success/20';
      case 'failed':
      case 'cancelled':
        return 'bg-destructive/10 text-destructive border-destructive/20';
      case 'running':
        return 'bg-primary/10 text-primary border-primary/20';
      case 'waiting_for_input':
        return 'bg-warning/10 text-warning border-warning/20';
      default:
        return 'bg-muted text-muted-foreground border-border';
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            {step === 'form' && 'Novo Mapeamento Interativo'}
            {step === 'mapping' && 'Mapeamento em Andamento'}
            {step === 'completed' && 'Mapeamento Concluído'}
          </DialogTitle>
          <DialogDescription>
            {step === 'form' && 'Configure um novo objetivo para mapeamento automático'}
            {step === 'mapping' && 'Acompanhe o progresso e forneça dados quando solicitado'}
            {step === 'completed' && 'Mapeamento finalizado com sucesso'}
          </DialogDescription>
        </DialogHeader>

        {step === 'form' && (
          <div className="space-y-6">
            {/* Objective Input */}
            <div className="space-y-2">
              <Label htmlFor="objective">
                Objetivo *
              </Label>
              <Input
                id="objective"
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="Ex: Consultar IPTU no site da prefeitura"
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Descreva em linguagem natural o que você quer automatizar
              </p>
            </div>

            {/* Starting URL */}
            <div className="space-y-2">
              <Label htmlFor="startingUrl" className="flex items-center gap-2">
                <Globe className="h-4 w-4" />
                URL Inicial (opcional)
              </Label>
              <Input
                id="startingUrl"
                value={startingUrl}
                onChange={(e) => setStartingUrl(e.target.value)}
                placeholder="https://exemplo.com"
                type="url"
                className="w-full"
              />
            </div>

            {/* Plan Name */}
            <div className="space-y-2">
              <Label htmlFor="planName" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Nome do Plano (opcional)
              </Label>
              <Input
                id="planName"
                value={planName}
                onChange={(e) => setPlanName(e.target.value)}
                placeholder="consulta_iptu"
                className="w-full"
              />
            </div>

            {/* Tags */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Tag className="h-4 w-4" />
                Tags
              </Label>
              <div className="flex gap-2">
                <Input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => handleKeyPress(e, addTag)}
                  placeholder="Adicionar tag..."
                  className="flex-1"
                />
                <Button onClick={addTag} variant="outline" size="sm">
                  Adicionar
                </Button>
              </div>
              {tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {tags.map((tag, index) => (
                    <Badge key={index} variant="secondary" className="text-xs">
                      {tag}
                      <button
                        onClick={() => removeTag(tag)}
                        className="ml-1 hover:text-red-500"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Error Display */}
            {error && (
              <Alert className="border-destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={handleClose}>
                Cancelar
              </Button>
              <Button onClick={startMapping} disabled={isLoading || !objective.trim()}>
                {isLoading ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Iniciando...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Iniciar Mapeamento
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {step === 'mapping' && session && (
          <div className="space-y-6">
            {/* Session Status */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Status do Mapeamento</CardTitle>
                  <Badge className={getStatusColor(session.status)}>
                    {getStatusIcon(session.status)}
                    <span className="ml-1 capitalize">{session.status.replace('_', ' ')}</span>
                  </Badge>
                </div>
                <CardDescription>
                  {session.objective}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Etapas Completadas</Label>
                    <p className="font-semibold">{session.steps_completed}</p>
                  </div>
                  
                  {/* Collected Parameters */}
                  {session.collected_parameters.length > 0 && (
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">Parâmetros Coletados</Label>
                      <div className="space-y-1 mt-1">
                        {session.collected_parameters.map((param, index) => (
                          <div key={index} className="flex justify-between text-sm">
                            <span className="text-muted-foreground">{param.label}:</span>
                            <span className="font-mono">{param.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Input Request */}
            {session.status === 'waiting_for_input' && session.current_input_request && (
              <Card className="border-warning/20 bg-warning/5">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Clock className="h-5 w-5 text-warning" />
                    Entrada Necessária
                  </CardTitle>
                  <CardDescription>
                    {session.current_input_request.prompt}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="inputValue">
                        {session.current_input_request.field_label}
                      </Label>
                      <Input
                        id="inputValue"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder={session.current_input_request.placeholder || `Digite ${session.current_input_request.field_label.toLowerCase()}`}
                        onKeyDown={(e) => handleKeyPress(e, submitInput)}
                        className="w-full"
                      />
                    </div>
                    <Button 
                      onClick={submitInput} 
                      disabled={isSubmittingInput || !inputValue.trim()}
                      className="w-full"
                    >
                      {isSubmittingInput ? (
                        <>
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                          Enviando...
                        </>
                      ) : (
                        <>
                          <Send className="mr-2 h-4 w-4" />
                          Enviar
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Error Display */}
            {error && (
              <Alert className="border-destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={handleClose}>
                Fechar
              </Button>
            </div>
          </div>
        )}

        {step === 'completed' && session && (
          <div className="space-y-6">
            {/* Success Message */}
            <Card className="border-success/20 bg-success/5">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-success" />
                  Mapeamento Concluído!
                </CardTitle>
                <CardDescription>
                  O objetivo foi mapeado com sucesso: "{session.objective}"
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">Etapas Completadas</Label>
                      <p className="font-semibold">{session.steps_completed}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">Parâmetros Coletados</Label>
                      <p className="font-semibold">{session.collected_parameters.length}</p>
                    </div>
                  </div>
                  
                  {/* Collected Parameters */}
                  {session.collected_parameters.length > 0 && (
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">Parâmetros do Plano</Label>
                      <div className="space-y-1 mt-1">
                        {session.collected_parameters.map((param, index) => (
                          <div key={index} className="flex justify-between text-sm">
                            <span className="text-muted-foreground">{param.label}:</span>
                            <span className="font-mono">{param.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Plan Creation */}
            {!createdPlan ? (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">Criar Plano</CardTitle>
                  <CardDescription>
                    Transforme o mapeamento em um plano executável
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="finalPlanName">Nome do Plano (opcional)</Label>
                      <Input
                        id="finalPlanName"
                        value={planName}
                        onChange={(e) => setPlanName(e.target.value)}
                        placeholder="Nome automático será gerado se vazio"
                        className="w-full"
                      />
                    </div>
                    <Button onClick={createPlan} disabled={isLoading} className="w-full" size="lg">
                      {isLoading ? (
                        <>
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                          Criando Plano...
                        </>
                      ) : (
                        <>
                          <FileText className="mr-2 h-4 w-4" />
                          Criar Plano
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-success/20 bg-success/5 animate-in fade-in-50 slide-in-from-top-2 duration-500">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-success" />
                    Plano Criado com Sucesso!
                  </CardTitle>
                  <CardDescription>
                    O plano "{createdPlan.metadata.name}" foi adicionado à sua lista de planos executáveis.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">ID do Plano</Label>
                      <p className="font-mono text-sm">{createdPlan.metadata.plan_id}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">Etapas</Label>
                      <p className="font-semibold">{createdPlan.steps.length}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">Parâmetros Necessários</Label>
                      <p className="font-semibold">{createdPlan.metadata.required_params.length}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Error Display */}
            {error && (
              <Alert className="border-destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2">
              {!createdPlan && (
                <Button variant="outline" onClick={handleClose}>
                  Fechar
                </Button>
              )}
              {createdPlan && (
                <Button onClick={handleCompleteAndClose} className="bg-success hover:bg-success/90">
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Concluir
                </Button>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}