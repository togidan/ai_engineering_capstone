import { useState, useRef, useEffect } from 'react'
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  Card,
  CardBody,
  Badge,
  Alert,
  AlertIcon,
  Spinner,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Input,
  FormControl,
  FormLabel,
  Progress,
  Divider,
  Stat,
  StatLabel,
  StatNumber,
  StatGroup
} from '@chakra-ui/react'
import { AttachmentIcon } from '@chakra-ui/icons'

interface UploadResponse {
  doc_id: number
  file_path: string
  filename: string
  file_size: number
  file_type: string
  description: string
  chunk_count: number
}

interface KBStats {
  database: {
    documents: number
    chunks: number
    indexed_chunks: number
    embedding_coverage: number
  }
  services: {
    milvus_available: boolean
    embeddings_available: boolean
  }
}

function KnowledgeBase() {
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null)
  const [error, setError] = useState('')
  const [stats, setStats] = useState<KBStats | null>(null)
  const [loadingStats, setLoadingStats] = useState(false)
  
  // File selection state
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setSelectedFile(file)
    setError('')
    setUploadResult(null)
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setUploading(true)
    setError('')
    setUploadResult(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      
      if (title) formData.append('title', title)
      if (sourceUrl) formData.append('source_url', sourceUrl)

      const response = await fetch(`${(import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'}/kb/upload`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Upload failed: ${response.statusText}`)
      }

      const result: UploadResponse = await response.json()
      setUploadResult(result)
      
      // Clear form
      setSelectedFile(null)
      setTitle('')
      setSourceUrl('')
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const loadStats = async () => {
    setLoadingStats(true)
    try {
      const response = await fetch(`${(import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'}/kb/stats`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to load stats:', err)
    } finally {
      setLoadingStats(false)
    }
  }

  // Load stats on mount
  useEffect(() => {
    loadStats()
  }, [])

  return (
    <VStack spacing={6} align="stretch">
      <Box>
        <Heading size="lg" mb={2}>Knowledge Base Management</Heading>
        <Text color="gray.600">
          Upload documents and manage the economic development knowledge base
        </Text>
      </Box>

      <Tabs>
        <TabList>
          <Tab>Upload Document</Tab>
          <Tab>Statistics</Tab>
        </TabList>

        <TabPanels>
          <TabPanel px={0}>
            <VStack spacing={6} align="stretch">
              <Card>
                <CardBody>
                  <VStack spacing={4} align="stretch">
                    <Heading size="md">Upload New Document</Heading>
                    
                    <FormControl>
                      <FormLabel>Select File</FormLabel>
                      <Input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.docx,.txt"
                        onChange={handleFileSelection}
                        disabled={uploading}
                        p={1}
                      />
                      <Text fontSize="sm" color="gray.500" mt={1}>
                        Supported formats: PDF, DOCX, TXT (max 10MB)
                      </Text>
                    </FormControl>

                    {selectedFile && (
                      <Card bg="blue.50" borderColor="blue.200">
                        <CardBody>
                          <VStack align="stretch" spacing={3}>
                            <Text fontWeight="bold" color="blue.700">Selected File</Text>
                            <VStack align="stretch" spacing={1} fontSize="sm">
                              <Text><strong>Name:</strong> {selectedFile.name}</Text>
                              <Text><strong>Size:</strong> {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</Text>
                              <Text><strong>Type:</strong> {selectedFile.type || 'Unknown'}</Text>
                            </VStack>
                          </VStack>
                        </CardBody>
                      </Card>
                    )}

                    <Divider />

                    <Text fontWeight="bold" fontSize="sm">
                      Optional Metadata (LLM will generate description automatically)
                    </Text>

                    <FormControl>
                      <FormLabel>Custom Title (optional)</FormLabel>
                      <Input
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        placeholder="Override the document title"
                        disabled={uploading}
                      />
                      <Text fontSize="xs" color="gray.500" mt={1}>
                        Leave blank to use LLM-generated title
                      </Text>
                    </FormControl>

                    <FormControl>
                      <FormLabel>Source URL (optional)</FormLabel>
                      <Input
                        value={sourceUrl}
                        onChange={(e) => setSourceUrl(e.target.value)}
                        placeholder="https://example.com/document"
                        disabled={uploading}
                      />
                    </FormControl>

                    <Button
                      colorScheme="blue"
                      size="lg"
                      leftIcon={<AttachmentIcon />}
                      onClick={handleUpload}
                      isDisabled={!selectedFile || uploading}
                      isLoading={uploading}
                      loadingText="Processing with LLM..."
                      w="full"
                    >
                      Upload Document
                    </Button>
                  </VStack>
                </CardBody>
              </Card>

              {uploading && (
                <Card>
                  <CardBody>
                    <VStack spacing={4}>
                      <Spinner size="lg" colorScheme="blue" />
                      <Text fontWeight="medium">Processing document with AI...</Text>
                      <VStack spacing={1} fontSize="sm" color="gray.600">
                        <Text>• Extracting text content</Text>
                        <Text>• Generating metadata with LLM</Text>
                        <Text>• Creating searchable chunks</Text>
                        <Text>• Building vector embeddings</Text>
                      </VStack>
                    </VStack>
                  </CardBody>
                </Card>
              )}

              {error && (
                <Alert status="error">
                  <AlertIcon />
                  {error}
                </Alert>
              )}

              {uploadResult && (
                <Alert status="success">
                  <AlertIcon />
                  <VStack align="stretch" spacing={2} flex={1}>
                    <Text fontWeight="bold">✅ Document uploaded successfully!</Text>
                    <VStack align="stretch" spacing={1} fontSize="sm">
                      <Text><strong>📄 File Name:</strong> {uploadResult.filename}</Text>
                      <Text><strong>📏 File Size:</strong> {(uploadResult.file_size / 1024 / 1024).toFixed(2)} MB</Text>
                      <Text><strong>📋 File Type:</strong> {uploadResult.file_type}</Text>
                      <Text><strong>🤖 Description:</strong> {uploadResult.description}</Text>
                      <Text><strong>🔢 Chunks Created:</strong> {uploadResult.chunk_count}</Text>
                      <Text fontSize="xs" color="gray.600"><strong>Document ID:</strong> {uploadResult.doc_id}</Text>
                    </VStack>
                  </VStack>
                </Alert>
              )}
            </VStack>
          </TabPanel>

          <TabPanel px={0}>
            <VStack spacing={4} align="stretch">
              <HStack justify="space-between">
                <Heading size="md">Knowledge Base Statistics</Heading>
                <Button onClick={loadStats} isLoading={loadingStats} size="sm">
                  Refresh
                </Button>
              </HStack>

              {stats && (
                <VStack spacing={4} align="stretch">
                  <Card>
                    <CardBody>
                      <StatGroup>
                        <Stat>
                          <StatLabel>Documents</StatLabel>
                          <StatNumber>{stats.database.documents}</StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Chunks</StatLabel>
                          <StatNumber>{stats.database.chunks}</StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Indexed</StatLabel>
                          <StatNumber>{stats.database.indexed_chunks}</StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Coverage</StatLabel>
                          <StatNumber>{(stats.database.embedding_coverage * 100).toFixed(1)}%</StatNumber>
                        </Stat>
                      </StatGroup>
                    </CardBody>
                  </Card>

                  <Card>
                    <CardBody>
                      <VStack align="stretch" spacing={3}>
                        <Heading size="sm">Service Status</Heading>
                        <HStack justify="space-between">
                          <Text>Vector Search (Milvus)</Text>
                          <Badge colorScheme={stats.services.milvus_available ? 'green' : 'red'}>
                            {stats.services.milvus_available ? 'Available' : 'Unavailable'}
                          </Badge>
                        </HStack>
                        <HStack justify="space-between">
                          <Text>Embeddings (OpenAI)</Text>
                          <Badge colorScheme={stats.services.embeddings_available ? 'green' : 'red'}>
                            {stats.services.embeddings_available ? 'Available' : 'Unavailable'}
                          </Badge>
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>

                  {stats.database.embedding_coverage < 1.0 && (
                    <Alert status="warning">
                      <AlertIcon />
                      <VStack align="stretch" fontSize="sm">
                        <Text fontWeight="bold">Some chunks are not indexed for search</Text>
                        <Text>
                          {stats.database.chunks - stats.database.indexed_chunks} chunks are missing embeddings. 
                          This may be due to service unavailability during upload.
                        </Text>
                      </VStack>
                    </Alert>
                  )}
                </VStack>
              )}
            </VStack>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </VStack>
  )
}

export default KnowledgeBase