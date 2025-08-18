import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  VStack,
  HStack,
  Text,
  Textarea,
  Button,
  Box,
  Alert,
  AlertIcon,
  Spinner,
  SimpleGrid,
  Badge,
  Divider,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  useToast
} from '@chakra-ui/react';
import { UploadIcon, SearchIcon, CopyIcon } from '@chakra-ui/icons';
import SlidingToggle from '../components/SlidingToggle';
import FileUpload from '../components/FileUpload';

interface RequirementRow {
  id: string;
  section: string;
  priority: string;
  requirement_text: string;
  normalized_key?: string;
  datatype: string;
  unit?: string;
  logic?: {
    threshold_min?: number;
    threshold_max?: number;
    options?: string[];
    format?: string;
  };
  answer_value?: string;
  status: string;
  source_field?: string;
  source_attachment?: string;
  confidence?: number;
  notes?: string;
}

interface AnalyzeResponse {
  requirements_table: RequirementRow[];
  summary: {
    met: number;
    not_met: number;
    unknown: number;
    critical_gaps: string[];
    data_sources_used: string[];
  };
  analysis_method?: string;
}

interface Citation {
  title: string;
  source_url?: string;
  file_path?: string;
  doc_type?: string;
  jurisdiction?: string;
}

interface DraftSection {
  heading: string;
  content: string;
}

interface DraftResponse {
  sections: DraftSection[];
  citations: Citation[];
  generation_method?: string;
  kb_context_used?: boolean;
}

const API_BASE_URL = 'http://localhost:8000';

// Load actual economic development data
async function loadEconomicData(): Promise<Record<string, any>> {
  try {
    // Load city data (assuming Columbus, OH as demo city)
    const response = await fetch('/data/cities.csv');
    const csvText = await response.text();
    
    // Parse CSV to find Columbus data
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',');
    const columbusLine = lines.find(line => line.includes('Columbus'));
    
    if (columbusLine) {
      const values = columbusLine.split(',');
      const cityData: Record<string, string> = {};
      headers.forEach((header, index) => {
        cityData[header.trim()] = values[index]?.trim() || '';
      });
      
      // Convert to economic development features with proper units and formatting
      return {
        // Location & Infrastructure
        city: cityData.city || 'Columbus',
        state: cityData.state || 'OH', 
        cbsa: cityData.cbsa || '18140',
        population: parseInt(cityData.pop || '2150000').toLocaleString(),
        
        // Workforce & Education  
        stem_share_pct: (parseFloat(cityData.stem_share || '0.145') * 100).toFixed(1),
        manufacturing_emp_share_pct: (parseFloat(cityData.manufacturing_emp_share || '0.105') * 100).toFixed(1),
        university_research_usd_m: (parseFloat(cityData.university_research_usd_m || '820000000') / 1000000).toFixed(0),
        
        // Sites & Utilities
        industrial_power_cents_kwh: parseFloat(cityData.industrial_power_cents_kwh || '7.8').toFixed(1),
        broadband_100_20_pct: (parseFloat(cityData.broadband_100_20_pct || '0.86') * 100).toFixed(1),
        
        // Economic Indicators
        median_income_usd: parseInt(cityData.median_income || '72000').toLocaleString(),
        median_rent_usd: parseInt(cityData.median_rent || '1200').toLocaleString(),
        logistics_index: parseFloat(cityData.logistics_index || '0.58').toFixed(2),
        
        // Additional typical economic development data points
        available_industrial_acres: '2,850', // Example - would come from additional data
        permitting_days_major: '90', // Example
        tax_increment_financing: 'Available',
        enterprise_zone_benefits: 'Available', 
        workforce_training_programs: '15+ programs available',
        major_highway_access: 'I-70, I-71, I-270',
        rail_access: 'CSX, Norfolk Southern',
        airport_distance_miles: '12',
        
        // Incentives & Programs
        property_tax_abatement: 'Up to 15 years available',
        job_creation_tax_credit: 'Up to $5,000 per job',
        research_development_credit: '8.5% of qualified expenses',
      };
    }
  } catch (error) {
    console.warn('Failed to load economic data, using fallback:', error);
  }
  
  // Fallback data if CSV loading fails
  return {
    city: 'Columbus',
    state: 'OH',
    cbsa: '18140',
    population: '2,150,000',
    stem_share_pct: '14.5',
    manufacturing_emp_share_pct: '10.5',
    university_research_usd_m: '820',
    industrial_power_cents_kwh: '7.8',
    broadband_100_20_pct: '86.0',
    median_income_usd: '72,000',
    median_rent_usd: '1,200',
    logistics_index: '0.58',
    available_industrial_acres: '2,850',
    permitting_days_major: '90',
    tax_increment_financing: 'Available',
    enterprise_zone_benefits: 'Available',
    workforce_training_programs: '15+ programs available',
    major_highway_access: 'I-70, I-71, I-270',
    rail_access: 'CSX, Norfolk Southern',
    airport_distance_miles: '12',
    property_tax_abatement: 'Up to 15 years available',
    job_creation_tax_credit: 'Up to $5,000 per job',
    research_development_credit: '8.5% of qualified expenses',
  };
}
const REAL_SAMPLE_RFP = `Request for Proposal (RFP)
Issued By: Orion Data Systems, Inc. (Hyperscale Cloud Infrastructure & Manufacturing Division)
RFP Number: ODS-2025-EDO-Expansion-001
Issue Date: August 9, 2025
Response Deadline: September 6, 2025, 5:00 PM EST

1. Introduction
Orion Data Systems, Inc. (“ODS”) is seeking proposals from qualified regional or local Economic Development Organizations (EDOs) to provide site, incentive, workforce, and infrastructure information for consideration in our site selection process for a new combined manufacturing and hyperscale data center campus in the United States.

The proposed facility will serve both as a manufacturing hub for server hardware and a data center cluster supporting Orion’s North American operations. This project is expected to generate significant investment in the selected region, including new construction, long-term skilled jobs, and local supplier opportunities.

2. Project Overview
ODS anticipates:

Capital Investment: Approx. $2.5 billion over 5 years

Facility Size: 500,000–750,000 sq. ft. initial phase, with expansion capacity up to 1.2 million sq. ft.

Jobs Created: 300–500 full-time positions (mix of manufacturing, data center operations, and corporate support)

Operational Timeline: Site selection Q4 2025, construction start Q2 2026, operational Q4 2027

3. Scope of RFP Response
Responding EDOs should provide detailed information in the following categories:

A. Site Information
Available properties (greenfield or brownfield) meeting the following criteria:

Minimum contiguous acreage: 75 acres (expandable)

Access to redundant fiber routes and high-capacity power feeds

Proximity to interstate or major transportation hubs (≤ 25 miles)

Zoning for industrial and/or data center use

Site ownership status and availability timeline

Environmental and geotechnical conditions (including wetlands, flood zones, seismic data)

B. Utility Infrastructure
Electric Power:

Capacity available now and in 24-month horizon

Reliability metrics (SAIDI/SAIFI)

Rates and tariff structures for large industrial/data center users

Water/Wastewater:

Capacity and availability for both cooling and manufacturing processes

Rate structures and any reuse/recycling options

Telecommunications:

Fiber providers and network redundancy options

Latency to major internet exchanges (Chicago, Dallas, Ashburn, etc.)

C. Workforce
Local and regional labor market data for relevant occupations

Training programs and workforce development initiatives available locally

Partnerships with universities, community colleges, and technical schools

Wage and benefit benchmarks

D. Incentives
State, regional, and local incentives (statutory and discretionary)

Fast-track permitting or regulatory support programs

Tax abatements, credits, and exemptions available

Infrastructure cost-sharing opportunities

E. Community and Quality of Life
Overview of the community and regional economic strengths

Housing availability and affordability for incoming workforce

Transportation infrastructure and public transit access

4. Proposal Format
Executive Summary

Detailed Responses (Sections A–E)

Appendices: Maps, data tables, letters of support, case studies of similar projects hosted

5. Evaluation Criteria
Responses will be evaluated on:

Completeness and relevance of information provided

Competitive positioning on utilities, incentives, and workforce readiness

Ability to meet project timelines

Long-term partnership potential with ODS

6. Submission Instructions
Please submit proposals in electronic format (PDF) to:
RFP@oriondatasystems.com
Subject Line: “RFP Response – [Your Region/EDO Name] – ODS-2025-EDO-Expansion-001”

Questions should be submitted by August 20, 2025 to the same email address. Answers will be distributed to all respondents.

Orion Data Systems, Inc.
Global Infrastructure & Operations Division
[Address]
[Phone Number]`;

const SAMPLE_RFP = `INDUSTRIAL DEVELOPMENT AUTHORITY
Request for Proposal - Economic Development Partnership

BACKGROUND & PROJECT SCOPE
The Greater Metro Industrial Development Authority seeks qualified economic development organizations, consulting firms, or joint ventures to provide comprehensive site selection and business attraction services. Our region needs to attract advanced manufacturing companies, particularly in automotive, aerospace, and clean energy sectors.

LOCATION REQUIREMENTS & INFRASTRUCTURE
* Must identify viable sites within 50-mile radius of downtown Metro City
* Minimum 150 contiguous acres for large manufacturers 
* Industrial power rates should be competitive (targeting <8.5¢/kWh)
* Railroad access preferred, Interstate highway access required
* Broadband: minimum 1 Gbps fiber connectivity
* Water/sewer capacity: minimum 2 MGD available
* Natural gas service with adequate pressure

WORKFORCE & EDUCATION CRITERIA
The selected consultant must evaluate our regional workforce capabilities including:
- Current STEM workforce percentage (seeking areas with >15% STEM employment)
- Manufacturing workforce availability 
- University research spending (preference for $500M+ annually)
- Community college technical programs aligned with target industries
- Workforce development partnerships

FINANCIAL REQUIREMENTS
Total project budget: $180,000 - $220,000 over 18 months
Payment schedule: 40% upon contract execution, 30% at 6-month milestone, 30% upon completion
Must provide detailed cost breakdown by task
Economic incentive analysis required for each recommended site

DELIVERABLES & TIMELINE
Phase 1 (Months 1-6): Regional assessment, site inventory, infrastructure analysis
Phase 2 (Months 7-12): Target industry analysis, competitive benchmarking  
Phase 3 (Months 13-18): Marketing materials, site certification, final recommendations

PROPOSAL SUBMISSION
Deadline: March 15, 2024, 3:00 PM EST
Electronic submission required (.pdf format, max 25 pages)
Must include: company overview, project approach, team qualifications, timeline, budget
References from similar engagements (minimum 3)

EVALUATION FACTORS:
- Technical approach and methodology (35%)
- Team experience and qualifications (30%)
- Understanding of regional assets (20%) 
- Cost competitiveness (15%)

Questions due by February 28, 2024. Oral presentations may be requested from shortlisted firms.

Contact: Sarah Mitchell, Economic Development Director
smitchell@metroida.org | (555) 123-4567`;

export default function Rfp() {
  const [rfpText, setRfpText] = useState('');
  const [inputMethod, setInputMethod] = useState<'paste' | 'upload'>('paste');
  const [analyzing, setAnalyzing] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResponse | null>(null);
  const [draftResult, setDraftResult] = useState<DraftResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const loadSampleRfp = () => {
    setRfpText(REAL_SAMPLE_RFP);
    setInputMethod('paste');
  };

  const handleFileContent = (content: string, filename: string) => {
    setRfpText(content);
    toast({
      title: 'File uploaded successfully',
      description: `Extracted text from ${filename}`,
      status: 'success',
      duration: 3000,
      isClosable: true,
    });
  };

  // Convert between our input method and toggle values
  const inputMethodToToggleValue = (method: 'paste' | 'upload'): 'left' | 'right' => {
    return method === 'paste' ? 'left' : 'right';
  };

  const toggleValueToInputMethod = (value: 'left' | 'right'): 'paste' | 'upload' => {
    return value === 'left' ? 'paste' : 'upload';
  };

  const handleToggleChange = (toggleValue: 'left' | 'right') => {
    const newInputMethod = toggleValueToInputMethod(toggleValue);
    setInputMethod(newInputMethod);
    // Clear analysis results when switching input methods
    setAnalysisResult(null);
    setDraftResult(null);
    setError(null);
  };

  const analyzeRfp = async (rfpText: string, features: Record<string, any>): Promise<AnalyzeResponse> => {
    const response = await fetch(`${API_BASE_URL}/rfi/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        rfp_text: rfpText,
        features
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to analyze RFP: ${response.statusText}`);
    }
    
    return response.json();
  };

  const draftRfi = async (
    rfpText: string, 
    features: Record<string, any>, 
    city?: string, 
    industry?: string
  ): Promise<DraftResponse> => {
    const response = await fetch(`${API_BASE_URL}/rfi/draft`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        rfp_text: rfpText,
        features,
        city,
        industry
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to draft RFI: ${response.statusText}`);
    }
    
    return response.json();
  };

  const handleAnalyze = async () => {
    if (!rfpText.trim()) {
      setError('Please provide RFP text to analyze');
      return;
    }

    setAnalyzing(true);
    setError(null);
    
    try {
      const features = await loadEconomicData();
      const result = await analyzeRfp(rfpText, features);
      setAnalysisResult(result);
    } catch (err) {
      console.error('Analysis failed:', err);
      setError('Failed to analyze RFP. Make sure the backend is running on localhost:8000');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDraftRfi = async () => {
    if (!analysisResult) {
      setError('Please analyze the RFP first');
      return;
    }

    setDrafting(true);
    setError(null);
    
    try {
      const features = await loadEconomicData();
      const result = await draftRfi(rfpText, features, 'Columbus', 'Economic Development');
      setDraftResult(result);
    } catch (err) {
      console.error('Draft generation failed:', err);
      setError('Failed to generate draft. Make sure the backend is running on localhost:8000');
    } finally {
      setDrafting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'met': return 'green';
      case 'not_met': return 'red';
      case 'unknown': return 'gray';
      default: return 'gray';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'yellow';
      case 'low': return 'green';
      default: return 'gray';
    }
  };

  const handleCopyDraft = async () => {
    if (!draftResult) return;
    
    const fullText = draftResult.sections
      .map(section => `${section.heading}\n\n${section.content}`)
      .join('\n\n---\n\n');
    
    try {
      await navigator.clipboard.writeText(fullText);
      toast({
        title: 'Copied to clipboard',
        description: 'The draft response has been copied to your clipboard',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    } catch (err) {
      toast({
        title: 'Failed to copy',
        description: 'Could not copy to clipboard',
        status: 'error',
        duration: 2000,
        isClosable: true,
      });
    }
  };

  return (
    <VStack spacing={6} align="stretch">
      <VStack spacing={4} align="stretch">
        <Text fontSize="2xl" fontWeight="bold" color="green.600">
          RFP Analysis & Response Drafting
        </Text>
        <Text color="gray.600">
          Upload your RFP document or paste the text to analyze requirements and generate a draft response
        </Text>
      </VStack>

      {error && (
        <Alert status="error">
          <AlertIcon />
          {error}
        </Alert>
      )}

      <Box p={6} bg="white" borderRadius="lg" shadow="md">
        <VStack spacing={6} align="stretch">
          <HStack justify="space-between" align="center">
            <Text fontSize="lg" fontWeight="semibold">
              RFP Input
            </Text>
            <Button size="sm" variant="outline" onClick={loadSampleRfp}>
              Load Sample RFP
            </Button>
          </HStack>

          <VStack spacing={4} align="start">
            <SlidingToggle
              leftLabel="Paste Text"
              rightLabel="Upload File"
              value={inputMethodToToggleValue(inputMethod)}
              onChange={handleToggleChange}
              colorScheme="blue"
            />

            {inputMethod === 'paste' ? (
              <Textarea
                value={rfpText}
                onChange={(e) => setRfpText(e.target.value)}
                placeholder="Paste your RFP text here or click 'Load Sample RFP' to see an example..."
                rows={12}
                resize="vertical"
                w="full"
              />
            ) : (
              <Box w="full">
                <FileUpload
                  onFileContent={handleFileContent}
                  acceptedFormats={['.txt', '.pdf', '.docx']}
                  maxSizeMB={10}
                />
                {rfpText && (
                  <Box mt={4} p={4} bg="gray.50" borderRadius="md" border="1px solid" borderColor="gray.200">
                    <Text fontSize="sm" color="gray.600" mb={2}>
                      Extracted Content Preview:
                    </Text>
                    <Text fontSize="sm" noOfLines={8}>
                      {rfpText}
                    </Text>
                    <Text fontSize="xs" color="gray.500" mt={2}>
                      {rfpText.length.toLocaleString()} characters, {rfpText.split(/\s+/).length.toLocaleString()} words
                    </Text>
                  </Box>
                )}
              </Box>
            )}
          </VStack>

          <Button
            leftIcon={<SearchIcon />}
            colorScheme="blue"
            size="lg"
            onClick={handleAnalyze}
            isLoading={analyzing}
            loadingText="Analyzing RFP..."
            isDisabled={!rfpText.trim()}
          >
            Analyze RFP
          </Button>
        </VStack>
      </Box>

      {analysisResult && (
        <Box p={6} bg="white" borderRadius="lg" shadow="md">
          <VStack spacing={6} align="stretch">
            <HStack justify="space-between" align="center">
              <VStack align="start" spacing={1}>
                <Text fontSize="lg" fontWeight="semibold">
                  Requirements Analysis
                </Text>
                <Badge 
                  colorScheme={analysisResult.analysis_method === 'llm' ? 'green' : 'gray'}
                  size="sm"
                >
                  {analysisResult.analysis_method === 'llm' ? 'AI Analysis' : 'Basic Analysis'}
                </Badge>
              </VStack>
              <SimpleGrid columns={4} spacing={4}>
                <VStack spacing={1}>
                  <Badge colorScheme="green" size="lg" px={3} py={1}>
                    {analysisResult.summary.met}
                  </Badge>
                  <Text fontSize="xs" color="gray.600">Met</Text>
                </VStack>
                <VStack spacing={1}>
                  <Badge colorScheme="red" size="lg" px={3} py={1}>
                    {analysisResult.summary.not_met}
                  </Badge>
                  <Text fontSize="xs" color="gray.600">Not Met</Text>
                </VStack>
                <VStack spacing={1}>
                  <Badge colorScheme="gray" size="lg" px={3} py={1}>
                    {analysisResult.summary.unknown}
                  </Badge>
                  <Text fontSize="xs" color="gray.600">Unknown</Text>
                </VStack>
                <VStack spacing={1}>
                  <Badge colorScheme="orange" size="lg" px={3} py={1}>
                    {analysisResult.summary.critical_gaps.length}
                  </Badge>
                  <Text fontSize="xs" color="gray.600">Critical Gaps</Text>
                </VStack>
              </SimpleGrid>
            </HStack>

            <Box overflowX="auto">
              <Table variant="simple" size="sm">
                <Thead bg="gray.50">
                  <Tr>
                    <Th>Section</Th>
                    <Th>Priority</Th>
                    <Th>Requirement</Th>
                    <Th>Answer</Th>
                    <Th>Status</Th>
                    <Th>Notes</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {analysisResult.requirements_table.map((req) => (
                    <Tr key={req.id} _hover={{ bg: 'gray.50' }}>
                      <Td>
                        <Badge variant="outline" colorScheme="blue" size="sm">
                          {req.section}
                        </Badge>
                      </Td>
                      
                      <Td>
                        <Badge colorScheme={getPriorityColor(req.priority)} size="sm">
                          {req.priority}
                        </Badge>
                      </Td>
                      
                      <Td maxW="300px">
                        <Text fontSize="sm" noOfLines={2}>
                          {req.requirement_text}
                        </Text>
                      </Td>
                      
                      <Td>
                        <Text 
                          fontSize="sm" 
                          color={req.answer_value === 'TODO' ? 'orange.500' : 'inherit'}
                          fontWeight={req.answer_value === 'TODO' ? 'bold' : 'normal'}
                        >
                          {req.answer_value || '-'}
                        </Text>
                      </Td>
                      
                      <Td>
                        <Badge colorScheme={getStatusColor(req.status)} size="sm">
                          {req.status.replace('_', ' ')}
                        </Badge>
                      </Td>
                      
                      <Td>
                        <Text fontSize="sm" color="gray.600">
                          {req.notes || '-'}
                        </Text>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>

            <Divider />

            <HStack justify="space-between" align="center">
              <VStack align="start" spacing={1}>
                <Text fontWeight="semibold">Ready to generate response?</Text>
                <Text fontSize="sm" color="gray.600">
                  Create a draft RFI response based on the analyzed requirements
                </Text>
              </VStack>
              <Button
                colorScheme="green"
                onClick={handleDraftRfi}
                isLoading={drafting}
                loadingText="Drafting..."
                leftIcon={<SearchIcon />}
              >
                Draft RFI Response
              </Button>
            </HStack>
          </VStack>
        </Box>
      )}

      {draftResult && (
        <Box p={6} bg="white" borderRadius="lg" shadow="md">
          <VStack spacing={6} align="stretch">
            <HStack justify="space-between" align="center">
              <VStack align="start" spacing={1}>
                <Text fontSize="lg" fontWeight="bold" color="green.600">
                  RFI Draft Response
                </Text>
                <HStack spacing={2}>
                  <Badge 
                    colorScheme={draftResult.generation_method === 'llm' ? 'green' : 'gray'}
                    size="sm"
                  >
                    {draftResult.generation_method === 'llm' ? 'AI Generated' : 'Template Generated'}
                  </Badge>
                  {draftResult.kb_context_used && (
                    <Badge colorScheme="blue" size="sm">
                      KB Enhanced
                    </Badge>
                  )}
                  {draftResult.citations && draftResult.citations.length > 0 && (
                    <Badge colorScheme="purple" size="sm">
                      {draftResult.citations.length} Citations
                    </Badge>
                  )}
                </HStack>
              </VStack>
              <Button
                leftIcon={<CopyIcon />}
                colorScheme="green"
                variant="outline"
                size="sm"
                onClick={handleCopyDraft}
              >
                Copy All
              </Button>
            </HStack>

            <VStack spacing={6} align="stretch">
              {draftResult.sections.map((section, index) => (
                <Box key={index}>
                  <Text fontSize="md" fontWeight="bold" color="blue.600" mb={3}>
                    {section.heading}
                  </Text>
                  
                  <Box
                    p={4}
                    bg="gray.50"
                    borderRadius="md"
                    border="1px solid"
                    borderColor="gray.200"
                  >
                    <Text fontSize="sm" whiteSpace="pre-line">
                      {section.content}
                    </Text>
                  </Box>
                  
                  {index < draftResult.sections.length - 1 && <Divider mt={4} />}
                </Box>
              ))}
            </VStack>

            {draftResult.citations && draftResult.citations.length > 0 && (
              <>
                <Divider />
                <VStack spacing={4} align="stretch">
                  <Text fontSize="md" fontWeight="bold" color="blue.600">
                    Sources & Citations
                  </Text>
                  <VStack spacing={3} align="stretch">
                    {draftResult.citations.map((citation, index) => (
                      <Box 
                        key={index}
                        p={3}
                        bg="blue.50"
                        borderRadius="md"
                        border="1px solid"
                        borderColor="blue.200"
                      >
                        <HStack justify="space-between" align="start">
                          <VStack align="stretch" spacing={1} flex={1}>
                            <Text fontSize="sm" fontWeight="semibold">
                              {citation.title}
                            </Text>
                            <HStack spacing={2} flexWrap="wrap">
                              {citation.jurisdiction && (
                                <Badge colorScheme="blue" size="sm">{citation.jurisdiction}</Badge>
                              )}
                              {citation.doc_type && (
                                <Badge colorScheme="purple" size="sm">{citation.doc_type}</Badge>
                              )}
                            </HStack>
                          </VStack>
                          {citation.source_url && (
                            <Button 
                              as="a" 
                              href={citation.source_url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              size="xs" 
                              colorScheme="blue" 
                              variant="outline"
                            >
                              View Source
                            </Button>
                          )}
                        </HStack>
                      </Box>
                    ))}
                  </VStack>
                </VStack>
              </>
            )}

            <Box pt={4} borderTop="1px solid" borderTopColor="gray.200">
              <Text fontSize="xs" color="gray.500" textAlign="center">
                This is a draft response generated from your RFP analysis. 
                Please review and customize before submitting.
              </Text>
            </Box>
          </VStack>
        </Box>
      )}

      <Box textAlign="center" pt={6}>
        <Button as={RouterLink} to="/" variant="outline">
          Back to Home
        </Button>
      </Box>
    </VStack>
  );
}