'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/app/components/ui/card';
import { Badge } from '@/app/components/ui/badge';
import { Label } from '@/app/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/app/components/ui/dialog';
import { 
  FileText, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  PlayCircle 
} from 'lucide-react';
import { ExecutionResult } from '@/app/services/types';
import { formatDuration } from '@/app/utils/utils';

interface ViewExecutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  execution: ExecutionResult | null;
}

export default function ViewExecutionModal({ isOpen, onClose, execution }: ViewExecutionModalProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-success" />;
      case 'failure':
      case 'error':
        return <XCircle className="h-5 w-5 text-destructive" />;
      case 'timeout':
        return <Clock className="h-5 w-5 text-warning" />;
      case 'partial_success':
        return <AlertCircle className="h-5 w-5 text-warning" />;
      default:
        return <PlayCircle className="h-5 w-5 text-primary" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-success/10 text-success border-success/20';
      case 'failure':
      case 'error':
        return 'bg-destructive/10 text-destructive border-destructive/20';
      case 'timeout':
        return 'bg-warning/10 text-warning border-warning/20';
      case 'partial_success':
        return 'bg-warning/10 text-warning border-warning/20';
      default:
        return 'bg-primary/10 text-primary border-primary/20';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="!w-[95vw] !max-w-none max-h-[90vh] overflow-y-auto" style={{ width: '95vw', maxWidth: 'none' }}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <PlayCircle className="h-5 w-5" />
            Detalhes da Execução: {execution?.execution_id}
          </DialogTitle>
          <DialogDescription>
            Visualize os detalhes completos desta execução do plano
          </DialogDescription>
        </DialogHeader>

        {execution && (
          <div className="space-y-4">
            {/* Execution Summary */}
            <div className="bg-muted/30 p-4 rounded-lg">
              <div className="grid gap-4 md:grid-cols-4">
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">Status</Label>
                  <div className="flex items-center gap-2 mt-1">
                    {getStatusIcon(execution.status)}
                    <Badge className={getStatusColor(execution.status)}>
                      {execution.status}
                    </Badge>
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">Progresso</Label>
                  <p className="font-semibold mt-1">
                    {execution.steps_completed}/{execution.total_steps} etapas
                  </p>
                </div>
                {execution.execution_time_ms && (
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Tempo de Execução</Label>
                    <p className="font-semibold mt-1">{formatDuration(execution.execution_time_ms)}</p>
                  </div>
                )}
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">ID da Execução</Label>
                  <p className="font-mono text-xs mt-1 break-all">{execution.execution_id}</p>
                </div>
              </div>
            </div>

            {/* Error Message */}
            {execution.error_message && (
              <Card className="border-destructive/20 bg-destructive/5">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <XCircle className="h-5 w-5 text-destructive" />
                    Erro de Execução
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm break-words bg-background p-3 rounded border">
                    {execution.error_message}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Artifacts */}
            {execution.artifacts.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3">Artefatos Gerados: {execution.artifacts.length}</h3>
                <div className="space-y-4">
                  {execution.artifacts.map((artifact, index) => (
                    <Card key={index} className="border-l-4 border-l-primary/20">
                      <CardHeader className="pb-3">
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs font-mono shrink-0">
                              #{index + 1}
                            </Badge>
                            <FileText className="h-5 w-5 text-primary" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <CardTitle className="text-base break-words">{artifact.name}</CardTitle>
                            <Badge variant="outline" className="text-xs mt-1">
                              {artifact.type}
                            </Badge>
                          </div>
                        </div>
                      </CardHeader>
                      
                      <CardContent className="pt-0">
                        <div className="space-y-4">
                          {/* Screenshot - Full Width */}
                          {artifact.type === 'screenshot' && artifact.content ? (
                            <div className="space-y-2">
                              <Label className="text-sm font-medium text-muted-foreground">Screenshot:</Label>
                              <div className="border rounded-lg p-3 bg-background">
                                <img 
                                  src={`data:image/png;base64,${artifact.content}`}
                                  alt={artifact.name}
                                  className="w-full h-auto rounded shadow-sm"
                                  style={{ maxHeight: '600px', objectFit: 'contain' }}
                                />
                              </div>
                            </div>
                          ) : artifact.content && (
                            <div className="space-y-2">
                              <Label className="text-sm font-medium text-muted-foreground">Conteúdo:</Label>
                              <div className="bg-muted p-3 rounded border font-mono text-sm overflow-hidden max-h-40 overflow-y-auto">
                                <pre className="whitespace-pre-wrap break-all text-wrap">
                                  {artifact.content}
                                </pre>
                              </div>
                            </div>
                          )}

                          {/* File Path */}
                          {artifact.file_path && (
                            <div className="space-y-2">
                              <Label className="text-sm font-medium text-muted-foreground">Caminho do Arquivo:</Label>
                              <p className="text-sm font-mono bg-muted/50 px-3 py-2 rounded break-all">
                                {artifact.file_path}
                              </p>
                            </div>
                          )}

                          {/* Metadata - Full Width */}
                          {Object.keys(artifact.metadata).length > 0 && (
                            <div className="space-y-2">
                              <Label className="text-sm font-medium text-muted-foreground">Metadados:</Label>
                              <div className="bg-muted/50 p-3 rounded border font-mono text-sm overflow-hidden max-h-60 overflow-y-auto">
                                <pre className="whitespace-pre-wrap break-all text-wrap">
                                  {JSON.stringify(artifact.metadata, null, 2)}
                                </pre>
                              </div>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* Execution Metadata */}
            {Object.keys(execution.metadata).length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3">Metadados da Execução</h3>
                <Card>
                  <CardContent className="pt-6">
                    <div className="bg-muted p-3 rounded border font-mono text-xs overflow-hidden">
                      <pre className="whitespace-pre-wrap break-all text-wrap">
                        {JSON.stringify(execution.metadata, null, 2)}
                      </pre>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}