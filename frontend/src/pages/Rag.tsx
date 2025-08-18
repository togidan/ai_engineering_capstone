import { useState } from 'react'
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Input,
  Button,
  Card,
  CardBody,
  Badge,
  Link,
  Alert,
  AlertIcon,
  Spinner,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Select,
  FormControl,
  FormLabel
} from '@chakra-ui/react'
import { SearchIcon } from '@chakra-ui/icons'

interface SearchHit {
  doc_id: number
  title: string
  jurisdiction?: string
  industry?: string
  doc_type?: string
  source_url?: string
  file_path: string
  text: string
  score: number
}

interface SearchResponse {
  hits: SearchHit[]
  out_of_scope: boolean
}

function Rag() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Filter state
  const [jurisdiction, setJurisdiction] = useState('')
  const [industry, setIndustry] = useState('')
  const [docType, setDocType] = useState('')

  const handleSearch = async () => {
    if (!query.trim()) return

    setLoading(true)
    setError('')
    
    try {
      const filters: Record<string, string> = {}
      if (jurisdiction) filters.jurisdiction = jurisdiction
      if (industry) filters.industry = industry
      if (docType) filters.doc_type = docType

      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/rag/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          k: 5,
          filters: Object.keys(filters).length > 0 ? filters : undefined
        })
      })

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
      }

      const data: SearchResponse = await response.json()
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <VStack spacing={6} align="stretch">
      <Box>
        <Heading size="lg" mb={2}>RAG Knowledge Search</Heading>
        <Text color="gray.600">
          Search economic development knowledge base with AI-powered semantic search
        </Text>
      </Box>

      <Tabs>
        <TabList>
          <Tab>Search</Tab>
          <Tab>Filters</Tab>
        </TabList>

        <TabPanels>
          <TabPanel px={0}>
            <VStack spacing={4} align="stretch">
              <HStack>
                <Input
                  placeholder="Search for economic development information..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  size="lg"
                />
                <Button
                  leftIcon={<SearchIcon />}
                  onClick={handleSearch}
                  isLoading={loading}
                  colorScheme="blue"
                  size="lg"
                >
                  Search
                </Button>
              </HStack>
            </VStack>
          </TabPanel>

          <TabPanel px={0}>
            <VStack spacing={4} align="stretch">
              <HStack spacing={4}>
                <FormControl>
                  <FormLabel>Jurisdiction</FormLabel>
                  <Select
                    placeholder="Any jurisdiction"
                    value={jurisdiction}
                    onChange={(e) => setJurisdiction(e.target.value)}
                  >
                    <option value="Ohio">Ohio</option>
                    <option value="Columbus, OH">Columbus, OH</option>
                    <option value="Cleveland, OH">Cleveland, OH</option>
                    <option value="Cincinnati, OH">Cincinnati, OH</option>
                    <option value="New York, NY">New York, NY</option>
                    <option value="Los Angeles, CA">Los Angeles, CA</option>
                    <option value="Chicago, IL">Chicago, IL</option>
                  </Select>
                </FormControl>

                <FormControl>
                  <FormLabel>Industry</FormLabel>
                  <Select
                    placeholder="Any industry"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                  >
                    <option value="manufacturing">Manufacturing</option>
                    <option value="biotech">Biotech</option>
                    <option value="logistics">Logistics</option>
                    <option value="cleantech">Cleantech</option>
                    <option value="aerospace">Aerospace</option>
                    <option value="software">Software</option>
                  </Select>
                </FormControl>

                <FormControl>
                  <FormLabel>Document Type</FormLabel>
                  <Select
                    placeholder="Any type"
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                  >
                    <option value="case_study">Case Study</option>
                    <option value="incentive">Incentive</option>
                    <option value="policy">Policy</option>
                    <option value="city_profile">City Profile</option>
                    <option value="economic_data">Economic Data</option>
                  </Select>
                </FormControl>
              </HStack>
            </VStack>
          </TabPanel>
        </TabPanels>
      </Tabs>

      {error && (
        <Alert status="error">
          <AlertIcon />
          {error}
        </Alert>
      )}

      {results && (
        <Box>
          {results.out_of_scope ? (
            <Alert status="warning">
              <AlertIcon />
              Your query appears to be outside the scope of economic development. 
              Please search for topics related to cities, incentives, workforce, infrastructure, or industry.
            </Alert>
          ) : (
            <VStack spacing={4} align="stretch">
              <Text fontWeight="bold">
                Found {results.hits.length} results
              </Text>
              
              {results.hits.map((hit) => (
                <Card key={hit.doc_id} variant="outline">
                  <CardBody>
                    <VStack align="stretch" spacing={3}>
                      <HStack justify="space-between" align="start">
                        <VStack align="stretch" spacing={1} flex={1}>
                          <Heading size="md">{hit.title}</Heading>
                          <HStack spacing={2} flexWrap="wrap">
                            {hit.jurisdiction && (
                              <Badge colorScheme="blue">{hit.jurisdiction}</Badge>
                            )}
                            {hit.industry && (
                              <Badge colorScheme="green">{hit.industry}</Badge>
                            )}
                            {hit.doc_type && (
                              <Badge colorScheme="purple">{hit.doc_type}</Badge>
                            )}
                          </HStack>
                        </VStack>
                        <Text fontSize="sm" color="gray.500">
                          Score: {(hit.score * 100).toFixed(1)}%
                        </Text>
                      </HStack>

                      <Text color="gray.700" lineHeight="tall">
                        {hit.text}
                      </Text>

                      <HStack spacing={4}>
                        {hit.source_url && (
                          <Link href={hit.source_url} isExternal color="blue.500">
                            View Source
                          </Link>
                        )}
                        <Text fontSize="sm" color="gray.500">
                          Document ID: {hit.doc_id}
                        </Text>
                      </HStack>
                    </VStack>
                  </CardBody>
                </Card>
              ))}
            </VStack>
          )}
        </Box>
      )}

      {loading && (
        <Box textAlign="center" py={8}>
          <Spinner size="lg" />
          <Text mt={2}>Searching knowledge base...</Text>
        </Box>
      )}
    </VStack>
  )
}

export default Rag