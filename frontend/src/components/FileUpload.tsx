import { useRef, useState, useCallback } from 'react';
import {
  Box,
  VStack,
  Text,
  Progress,
  Alert,
  AlertIcon,
  HStack,
  Icon
} from '@chakra-ui/react';
import { AttachmentIcon, CheckCircleIcon } from '@chakra-ui/icons';

interface FileUploadProps {
  onFileContent: (content: string, filename: string) => void;
  acceptedFormats?: string[];
  maxSizeMB?: number;
}

interface UploadResult {
  success: boolean;
  filename: string;
  text: string;
  char_count: number;
  word_count: number;
}

const API_BASE_URL = 'http://localhost:8000';

export default function FileUpload({
  onFileContent,
  acceptedFormats = ['.txt', '.pdf', '.docx'],
  maxSizeMB = 10
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadFile = async (file: File): Promise<void> => {
    setError(null);
    setUploadSuccess(null);
    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Create FormData
      const formData = new FormData();
      formData.append('file', file);

      // Simulate progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 100);

      // Upload file
      const response = await fetch(`${API_BASE_URL}/rfi/upload`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Upload failed: ${response.statusText}`);
      }

      const result: UploadResult = await response.json();
      
      if (result.success && result.text) {
        setUploadSuccess(`Successfully extracted ${result.char_count.toLocaleString()} characters from ${result.filename}`);
        onFileContent(result.text, result.filename);
      } else {
        throw new Error('Failed to extract text from file');
      }

    } catch (err) {
      console.error('File upload failed:', err);
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
      setTimeout(() => {
        setUploadProgress(0);
        setUploadSuccess(null);
      }, 3000);
    }
  };

  const handleFile = useCallback(async (file: File) => {
    // Validate file type
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedFormats.includes(fileExtension)) {
      setError(`Unsupported file format. Accepted formats: ${acceptedFormats.join(', ')}`);
      return;
    }

    // Validate file size
    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File too large. Maximum size is ${maxSizeMB}MB.`);
      return;
    }

    await uploadFile(file);
  }, [acceptedFormats, maxSizeMB]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFile(files[0]);
    }
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileSelect = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  }, [handleFile]);

  return (
    <VStack spacing={4} align="stretch">
      {error && (
        <Alert status="error">
          <AlertIcon />
          {error}
        </Alert>
      )}

      {uploadSuccess && (
        <Alert status="success">
          <AlertIcon />
          {uploadSuccess}
        </Alert>
      )}

      <Box
        border="2px dashed"
        borderColor={isDragging ? "blue.400" : "gray.300"}
        borderRadius="lg"
        p={8}
        textAlign="center"
        bg={isDragging ? "blue.50" : "gray.50"}
        transition="all 0.2s ease"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        cursor="pointer"
        onClick={handleFileSelect}
        _hover={{
          borderColor: "blue.400",
          bg: "blue.50"
        }}
      >
        <VStack spacing={4}>
          <Icon 
            as={uploadSuccess ? CheckCircleIcon : AttachmentIcon} 
            w={12} 
            h={12} 
            color={uploadSuccess ? "green.500" : isDragging ? "blue.500" : "gray.400"}
          />
          
          {isUploading ? (
            <VStack spacing={2} w="full">
              <Text fontWeight="medium">Uploading file...</Text>
              <Progress value={uploadProgress} colorScheme="blue" w="full" />
            </VStack>
          ) : (
            <VStack spacing={2}>
              <Text fontWeight="medium" color="gray.700">
                Drop your RFP file here or click to browse
              </Text>
              <HStack spacing={1}>
                <Text fontSize="sm" color="gray.500">
                  Supported formats:
                </Text>
                <Text fontSize="sm" color="blue.600" fontWeight="medium">
                  {acceptedFormats.join(', ')}
                </Text>
              </HStack>
              <Text fontSize="sm" color="gray.500">
                Maximum file size: {maxSizeMB}MB
              </Text>
            </VStack>
          )}
        </VStack>

        <input
          ref={fileInputRef}
          type="file"
          hidden
          accept={acceptedFormats.join(',')}
          onChange={handleFileInputChange}
        />
      </Box>
    </VStack>
  );
}