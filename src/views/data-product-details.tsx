import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DataProduct, InputPort, OutputPort, DataProductStatus, DataProductArchetype, DataProductOwner } from '@/types/data-product'; // Import Port types
import DataProductFormDialog from '@/components/data-products/data-product-form-dialog';
import { useApi } from '@/hooks/use-api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Pencil, Trash2, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Toaster } from '@/components/ui/toaster';
import { useToast } from '@/hooks/use-toast';
import { Label } from '@/components/ui/label';
import useBreadcrumbStore from '@/stores/breadcrumb-store'; // Import Zustand store

// Helper Function Type Definition (copied from DataProducts view for checking API responses)
type CheckApiResponseFn = <T>(
    response: { data?: T | { detail?: string }, error?: string },
    name: string
) => T;

// Helper Function Implementation
const checkApiResponse: CheckApiResponseFn = (response, name) => {
    if (response.error) {
        throw new Error(`${name} fetch failed: ${response.error}`);
    }
    if (response.data && typeof response.data === 'object' && 'detail' in response.data && typeof response.data.detail === 'string') {
        throw new Error(`${name} fetch failed: ${response.data.detail}`);
    }
    if (response.data === null || response.data === undefined) {
        throw new Error(`${name} fetch returned null or undefined data.`);
    }
    return response.data as any;
};

export default function DataProductDetails() {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const api = useApi();
  const { get } = api; // Destructure get method here
  const { toast } = useToast();
  const setDynamicBreadcrumbTitle = useBreadcrumbStore((state) => state.setDynamicTitle); // Get setter action

  const [product, setProduct] = useState<DataProduct | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false); // State for edit dialog

  // State for dropdown values needed by the dialog
  const [statuses, setStatuses] = useState<DataProductStatus[]>([]);
  const [archetypes, setArchetypes] = useState<DataProductArchetype[]>([]);
  const [owners, setOwners] = useState<DataProductOwner[]>([]);

  // Helper to format dates safely
  const formatDate = (dateString: string | undefined): string => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch (e) {
      return 'Invalid Date';
    }
  };

  // Helper to get status badge variant
  const getStatusColor = (status: string | undefined): 'default' | 'secondary' | 'destructive' | 'outline' => {
    switch (status?.toLowerCase()) {
      case 'production': return 'default';
      case 'development': return 'secondary';
      case 'deprecated': return 'destructive';
      default: return 'outline';
    }
  };

  // Function to fetch product details and dropdown data
  const fetchDetailsAndDropdowns = async () => {
    if (!productId) {
      setError('Product ID not found in URL.');
      setDynamicBreadcrumbTitle(null); // Clear title if ID is missing
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    setDynamicBreadcrumbTitle('Loading...'); // Set loading state
    try {
      // Fetch product details and dropdown values concurrently
      const [productResp, statusesResp, archetypesResp, ownersResp] = await Promise.all([
        get<DataProduct>(`/api/data-products/${productId}`),
        get<DataProductStatus[]>('/api/data-products/statuses'),
        get<DataProductArchetype[]>('/api/data-products/archetypes'),
        get<DataProductOwner[]>('/api/data-products/owners'),
      ]);

      // Check responses using the helper
      const productData = checkApiResponse(productResp, 'Product Details');
      const statusesData = checkApiResponse(statusesResp, 'Statuses');
      const archetypesData = checkApiResponse(archetypesResp, 'Archetypes');
      const ownersData = checkApiResponse(ownersResp, 'Owners');

      // Set state
      setProduct(productData);
      setStatuses(Array.isArray(statusesData) ? statusesData : []);
      setArchetypes(Array.isArray(archetypesData) ? archetypesData : []);
      setOwners(Array.isArray(ownersData) ? ownersData : []);

      // Update breadcrumb store with the actual title
      setDynamicBreadcrumbTitle(productData.info.title);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch data';
      setError(errorMessage);
      setProduct(null); // Clear product on error
      // Clear dropdowns on error too?
      setStatuses([]);
      setArchetypes([]);
      setOwners([]);
      setDynamicBreadcrumbTitle('Error'); // Set error state or null
      toast({ title: 'Error', description: `Failed to load data: ${errorMessage}`, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and cleanup
  useEffect(() => {
    fetchDetailsAndDropdowns();
    
    // Cleanup function: Clear the title when the component unmounts
    return () => {
        console.log("DataProductDetails unmounting, clearing breadcrumb title.");
        setDynamicBreadcrumbTitle(null);
    };
    // We only want to fetch initially or if productId changes.
  }, [productId, get, toast, setDynamicBreadcrumbTitle]); // Add setDynamicBreadcrumbTitle to deps

  const handleEdit = () => {
    if (!product) {
        toast({ title: 'Error', description: 'Product data not loaded yet.', variant: 'destructive' });
        return;
    }
    setIsEditDialogOpen(true); // Open the dialog
  };

  // Handler for successful dialog submission
  const handleDialogSubmitSuccess = (savedProduct: DataProduct) => {
    console.log('Edit dialog submitted successfully, refreshing details...', savedProduct);
    setIsEditDialogOpen(false); // Close the dialog
    fetchDetailsAndDropdowns(); // Refetch details to show updates
  };

  const handleDelete = async () => {
    if (!productId || !product) return;
    // Use info.title for confirmation
    if (!confirm(`Are you sure you want to delete data product "${product.info.title}"?`)) return;

    try {
      await api.delete(`/api/data-products/${productId}`);
      toast({ title: 'Success', description: 'Data product deleted successfully.' });
      navigate('/data-products'); // Navigate back to the list view
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete product';
      toast({ title: 'Error', description: `Failed to delete: ${errorMessage}`, variant: 'destructive' });
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  // Not found state
  if (!product) {
    return (
      <Alert>
        <AlertDescription>Data product not found.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="py-6 space-y-6">
      <div className="flex justify-between items-start">
        <h1 className="text-3xl font-bold mb-2">{product.info.title}</h1>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={handleEdit} disabled={!product}>
            <Pencil className="mr-2 h-4 w-4" /> Edit
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={!product}>
            <Trash2 className="mr-2 h-4 w-4" /> Delete
          </Button>
        </div>
      </div>

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-3 gap-4">
            <div className="space-y-1"><Label>Owner:</Label> <span className="text-sm block">{product.info.owner}</span></div>
            <div className="space-y-1"><Label>Domain:</Label> <span className="text-sm block">{product.info.domain || 'N/A'}</span></div>
            <div className="space-y-1">
              <Label>Status:</Label>
              <Badge variant={getStatusColor(product.info.status)} className="ml-1">{product.info.status || 'N/A'}</Badge>
            </div>
             <div className="space-y-1"><Label>Archetype:</Label> <span className="text-sm block">{product.info.archetype || 'N/A'}</span></div>
             <div className="space-y-1"><Label>Created:</Label> <span className="text-sm block">{formatDate(product.created_at)}</span></div>
             <div className="space-y-1"><Label>Updated:</Label> <span className="text-sm block">{formatDate(product.updated_at)}</span></div>
             <div className="space-y-1"><Label>Spec Version:</Label> <span className="text-sm block">{product.dataProductSpecification}</span></div>
          </div>
          <div className="space-y-1"><Label>Description:</Label> <p className="text-sm mt-1">{product.info.description || 'N/A'}</p></div>
          <div className="space-y-1">
            <Label>Tags:</Label>
            <div className="flex flex-wrap gap-1 mt-1">
              {(product.tags || []).length > 0 ? (
                product.tags.map((tag: string) => (
                  <Badge key={tag} variant="secondary">{tag}</Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">No tags</span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Ports Card */}
      <Card>
        <CardHeader>
          <CardTitle>Ports</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-medium mb-2 text-base">Input Ports</h4>
            {(product.inputPorts?.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">No input ports defined.</p>
            ) : (
              product.inputPorts.map((port: InputPort, index: number) => (
                <div key={`input-${index}-${port.id}`} className="border p-3 rounded mb-2 space-y-1">
                  <p className="font-semibold text-sm">{port.name} <span className="text-xs text-muted-foreground">(ID: {port.id})</span></p>
                  <p className="text-xs"><span className="text-muted-foreground">Source System ID:</span> {port.sourceSystemId}</p>
                  {port.description && <p className="text-xs"><span className="text-muted-foreground">Description:</span> {port.description}</p>}
                  {/* TODO: Display port tags, links, custom props? */}
                </div>
              ))
            )}
          </div>
          <div>
            <h4 className="font-medium mb-2 text-base">Output Ports</h4>
             {(product.outputPorts?.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">No output ports defined.</p>
            ) : (
              product.outputPorts.map((port: OutputPort, index: number) => (
                 <div key={`output-${index}-${port.id}`} className="border p-3 rounded mb-2 space-y-1">
                  <p className="font-semibold text-sm">{port.name} <span className="text-xs text-muted-foreground">(ID: {port.id})</span></p>
                  {port.description && <p className="text-xs"><span className="text-muted-foreground">Description:</span> {port.description}</p>}
                   {port.status && <p className="text-xs"><span className="text-muted-foreground">Status:</span> <Badge variant={getStatusColor(port.status)} className="ml-1">{port.status}</Badge></p>}
                   {port.dataContractId && <p className="text-xs"><span className="text-muted-foreground">Data Contract ID:</span> {port.dataContractId}</p>}
                   {/* TODO: Display output port server info, containsPii, autoApprove, tags, links, custom? */}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* TODO: Add Cards for Links, Custom Properties, etc. */}

      {/* Render the reusable Edit Dialog component */} 
      {isEditDialogOpen && product && (
        <DataProductFormDialog
            isOpen={isEditDialogOpen}
            onOpenChange={setIsEditDialogOpen} // Let dialog control closing via state
            initialProduct={product} // Pass the current product data
            statuses={statuses}
            archetypes={archetypes}
            owners={owners}
            api={api} // Pass the full api object
            onSubmitSuccess={handleDialogSubmitSuccess} // Pass the success handler
        />
      )}

      <Toaster />
    </div>
  );
} 