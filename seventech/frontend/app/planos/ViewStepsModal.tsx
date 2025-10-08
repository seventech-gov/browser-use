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
import { FileText } from 'lucide-react';
import { Plan } from '@/app/services/types';

interface ViewStepsModalProps {
  isOpen: boolean;
  onClose: () => void;
  plan: Plan | null;
}

export default function ViewStepsModal({ isOpen, onClose, plan }: ViewStepsModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="!w-[95vw] !max-w-none max-h-[90vh] overflow-y-auto" style={{ width: '95vw', maxWidth: 'none' }}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Steps do Plano: {plan?.metadata.name}
          </DialogTitle>
          <DialogDescription>
            Visualize todas as etapas que compõem este plano de automação
          </DialogDescription>
        </DialogHeader>

        {plan && (
          <div className="space-y-4">
            {/* Steps List */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Sequência de Execução: {plan.steps.length}</h3>
              
              {plan.steps.map((step) => (
                <Card key={step.sequence_id} className="border-l-4 border-l-primary/20">
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-3 mb-3">
                      <Badge variant="outline" className="text-xs font-mono shrink-0">
                        #{step.sequence_id + 1}
                      </Badge>
                      <CardTitle className="text-base">{step.action}</CardTitle>
                    </div>
                    {step.description && (
                      <div className="space-y-1">
                        <Label className="text-sm font-medium text-muted-foreground">Descrição:</Label>
                        <p className="text-sm break-words bg-muted/30 p-2 rounded">
                          {step.description}
                        </p>
                      </div>
                    )}
                  </CardHeader>
                  
                  {Object.keys(step.params).length > 0 && (
                    <CardContent className="pt-0">
                      <div className="space-y-2">
                        <Label className="text-sm font-medium text-muted-foreground">Parâmetros:</Label>
                        <div className="bg-muted p-3 rounded border font-mono text-xs overflow-hidden">
                          <pre className="whitespace-pre-wrap break-all text-wrap">
                            {JSON.stringify(step.params, null, 2)}
                          </pre>
                        </div>
                      </div>

                      {/* Original action if different */}
                      {step.original_action && step.original_action !== step.action && (
                        <div className="mt-3 pt-3 border-t">
                          <Label className="text-sm font-medium text-muted-foreground">Ação Original:</Label>
                          <p className="text-sm font-mono bg-muted/50 px-2 py-1 rounded mt-1">
                            {step.original_action}
                          </p>
                          {step.original_params && (
                            <div className="mt-2">
                              <Label className="text-sm font-medium text-muted-foreground">Parâmetros Originais:</Label>
                              <div className="bg-muted/50 p-2 rounded border font-mono text-xs mt-1 overflow-hidden">
                                <pre className="whitespace-pre-wrap break-all text-wrap">
                                  {JSON.stringify(step.original_params, null, 2)}
                                </pre>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}