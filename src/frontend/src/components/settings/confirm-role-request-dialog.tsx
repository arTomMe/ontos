import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';

interface ConfirmRoleRequestDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  requesterEmail: string;
  roleId: string;
  roleName: string;
  onDecisionMade: () => void; // Callback after decision is submitted
}

const ConfirmRoleRequestDialog: React.FC<ConfirmRoleRequestDialogProps> = ({
  isOpen,
  onOpenChange,
  requesterEmail,
  roleId,
  roleName,
  onDecisionMade,
}) => {
  const [decisionMessage, setDecisionMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { post } = useApi();
  const { toast } = useToast();

  const handleSubmit = async (approved: boolean) => {
    setIsSubmitting(true);
    try {
        const payload = {
            requester_email: requesterEmail,
            role_id: roleId,
            approved: approved,
            message: decisionMessage,
        };
        
        // Wrap the payload under the key expected by the backend
        const requestBody = { request_data: payload };

        // Send the nested request body
        const response = await post('/api/settings/roles/handle-request', requestBody);
        if (response.error) {
             throw new Error(response.error);
        }

        toast({
            title: `Request ${approved ? 'Approved' : 'Denied'}`,
            description: `Decision for ${requesterEmail}'s request for role ${roleName} submitted.`,
        });
        onDecisionMade(); // Notify parent component
        onOpenChange(false); // Close the dialog
    } catch (err: any) {
        toast({
            title: 'Submission Failed',
            description: err.message || 'Could not submit the decision.',
            variant: 'destructive',
        });
    } finally {
        setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Handle Role Access Request</DialogTitle>
          <DialogDescription>
            Review the request from <strong>{requesterEmail}</strong> for the role <strong>{roleName}</strong>.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
            <Label htmlFor="decision-message">Optional Message to Requester</Label>
            <Textarea
                id="decision-message"
                value={decisionMessage}
                onChange={(e) => setDecisionMessage(e.target.value)}
                placeholder="Provide a reason for approval or denial (optional)"
                className="mt-1"
                disabled={isSubmitting}
            />
        </div>
        <DialogFooter className="gap-2 sm:justify-between">
            <Button
                variant="destructive"
                onClick={() => handleSubmit(false)}
                disabled={isSubmitting}
            >
                {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Deny Request
            </Button>
           <div className="flex gap-2">
             <DialogClose asChild>
                <Button variant="outline" disabled={isSubmitting}>Cancel</Button>
            </DialogClose>
            <Button 
                onClick={() => handleSubmit(true)}
                disabled={isSubmitting}
            >
                {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Approve Request
            </Button>
           </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ConfirmRoleRequestDialog; 