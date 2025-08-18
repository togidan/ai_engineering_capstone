import { useState, useEffect } from 'react';
import { useSearchParams, Link as RouterLink } from 'react-router-dom';
import {
  VStack,
  HStack,
  Text,
  Button,
  Box,
  SimpleGrid,
  Spinner,
  Alert,
  AlertIcon,
  Badge,
  Progress,
  List,
  ListItem,
  ListIcon
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';

interface City {
  city: string;
  state: string;
  pop: number;
  cbsa: string;
  median_income: number;
  stem_share: number;
  manufacturing_emp_share: number;
  median_rent: number;
  industrial_power_cents_kwh: number;
  broadband_100_20_pct: number;
  university_research_usd_m: number;
  logistics_index: number;
}

interface Industry {
  id: string;
  name: string;
  description: string;
  weights: Record<string, number>;
  thresholds: Record<string, number>;
  prescriptions: {
    strengths: string[];
    opportunities: string[];
    concerns: string[];
  };
}

interface IndustryScore {
  industry: Industry;
  score: number;
  normalizedScore: number;
  strengths: string[];
  gaps: string[];
}

async function loadCities(): Promise<City[]> {
  const response = await fetch('/data/cities.csv');
  const csvText = await response.text();
  
  const lines = csvText.trim().split('\n');
  const headers = lines[0].split(',');
  
  return lines.slice(1).map(line => {
    const values = line.split(',');
    const city: any = {};
    
    headers.forEach((header, index) => {
      const value = values[index];
      
      if (header === 'city' || header === 'cbsa' || header === 'state') {
        city[header] = value;
      } else {
        city[header] = parseFloat(value);
      }
    });
    
    return city as City;
  });
}

async function loadIndustries(): Promise<Industry[]> {
  const response = await fetch('/data/industries.json');
  return response.json();
}

function scoreIndustry(city: City, industry: Industry): IndustryScore {
  let weightedScore = 0;
  let totalWeight = 0;
  
  // Calculate weighted score
  Object.entries(industry.weights).forEach(([metric, weight]) => {
    if (metric in city) {
      const value = (city as any)[metric];
      let normalizedValue = 0;
      
      // Simple normalization - in a real app, you'd use the bounds.json
      switch (metric) {
        case 'median_rent':
        case 'industrial_power_cents_kwh':
          // Lower is better
          normalizedValue = Math.max(0, 1 - (value / 2000)); // rough normalization
          break;
        default:
          // Higher is better
          normalizedValue = Math.min(1, value / 100000000); // very rough normalization
          if (metric.includes('_share') || metric.includes('_pct')) {
            normalizedValue = Math.min(1, value * 5); // percentage metrics
          }
          break;
      }
      
      weightedScore += normalizedValue * weight;
      totalWeight += weight;
    }
  });
  
  const finalScore = totalWeight > 0 ? weightedScore / totalWeight : 0;
  const normalizedScore = Math.round(finalScore * 100);
  
  // Generate strengths and gaps based on score
  const strengths = industry.prescriptions.strengths.slice(0, Math.floor(normalizedScore / 30));
  const gaps = industry.prescriptions.concerns.slice(0, Math.floor((100 - normalizedScore) / 30));
  
  return {
    industry,
    score: finalScore,
    normalizedScore,
    strengths,
    gaps
  };
}

export default function Results() {
  const [searchParams] = useSearchParams();
  const cityName = searchParams.get('city');
  const stateName = searchParams.get('state');
  
  const [city, setCity] = useState<City | null>(null);
  const [industryScores, setIndustryScores] = useState<IndustryScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      if (!cityName || !stateName) {
        setError('City and state parameters are required');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const [cities, industries] = await Promise.all([
          loadCities(),
          loadIndustries()
        ]);

        const selectedCity = cities.find(
          c => c.city.toLowerCase() === cityName.toLowerCase() && 
               c.state.toLowerCase() === stateName.toLowerCase()
        );

        if (!selectedCity) {
          setError(`City "${cityName}, ${stateName}" not found`);
          setLoading(false);
          return;
        }

        setCity(selectedCity);

        const scores = industries
          .map(industry => scoreIndustry(selectedCity, industry))
          .sort((a, b) => b.normalizedScore - a.normalizedScore);
        
        setIndustryScores(scores);

      } catch (err) {
        console.error('Failed to load data:', err);
        setError('Failed to load city opportunity data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [cityName, stateName]);

  if (loading) {
    return (
      <VStack spacing={4} align="center" py={8}>
        <Spinner size="xl" color="blue.500" />
        <Text>Loading city opportunity data...</Text>
      </VStack>
    );
  }

  if (error) {
    return (
      <VStack spacing={4} align="stretch">
        <Alert status="error">
          <AlertIcon />
          {error}
        </Alert>
        <Box textAlign="center">
          <Button as={RouterLink} to="/" colorScheme="blue">
            Back to Home
          </Button>
        </Box>
      </VStack>
    );
  }

  if (!city) {
    return (
      <VStack spacing={4} align="stretch">
        <Alert status="warning">
          <AlertIcon />
          City data not found
        </Alert>
        <Box textAlign="center">
          <Button as={RouterLink} to="/" colorScheme="blue">
            Back to Home
          </Button>
        </Box>
      </VStack>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      <VStack spacing={4} align="stretch">
        <Text fontSize="2xl" fontWeight="bold" color="blue.600">
          Industry Opportunities in {city.city}, {city.state}
        </Text>
        
        <Box p={6} bg="white" borderRadius="lg" shadow="sm">
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={6}>
            <VStack>
              <Text fontSize="2xl" fontWeight="bold" color="blue.600">
                {city.pop.toLocaleString()}
              </Text>
              <Text fontSize="sm" color="gray.600">Population</Text>
            </VStack>
            <VStack>
              <Text fontSize="2xl" fontWeight="bold" color="green.600">
                ${city.median_income.toLocaleString()}
              </Text>
              <Text fontSize="sm" color="gray.600">Median Income</Text>
            </VStack>
            <VStack>
              <Text fontSize="2xl" fontWeight="bold" color="purple.600">
                {Math.round(city.stem_share * 100)}%
              </Text>
              <Text fontSize="sm" color="gray.600">STEM Share</Text>
            </VStack>
            <VStack>
              <Text fontSize="2xl" fontWeight="bold" color="orange.600">
                ${city.median_rent.toLocaleString()}
              </Text>
              <Text fontSize="sm" color="gray.600">Median Rent</Text>
            </VStack>
          </SimpleGrid>
        </Box>
      </VStack>

      <VStack spacing={4} align="stretch">
        <HStack justify="space-between" align="center">
          <Text fontSize="xl" fontWeight="bold">
            Top Industry Opportunities
          </Text>
          <Text fontSize="sm" color="gray.600">
            Based on {industryScores.length} industries analyzed
          </Text>
        </HStack>

        <SimpleGrid columns={{ base: 1, lg: 2, xl: 3 }} spacing={6}>
          {industryScores.slice(0, 6).map((score, index) => {
            const getScoreColor = (score: number) => {
              if (score >= 70) return 'green';
              if (score >= 50) return 'yellow';
              return 'red';
            };
            
            const scoreColor = getScoreColor(score.normalizedScore);
            
            return (
              <Box
                key={score.industry.id}
                p={6}
                bg="white"
                border="1px solid"
                borderColor="gray.200"
                borderRadius="lg"
                shadow="md"
                position="relative"
              >
                <Badge
                  position="absolute"
                  top={2}
                  right={2}
                  colorScheme="blue"
                  variant="solid"
                  borderRadius="full"
                  px={3}
                  py={1}
                >
                  #{index + 1}
                </Badge>
                
                <VStack align="stretch" spacing={4}>
                  <VStack align="stretch" spacing={2}>
                    <Text fontSize="xl" fontWeight="bold" color={`${scoreColor}.600`}>
                      {score.industry.name}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      {score.industry.description}
                    </Text>
                  </VStack>

                  <HStack justify="space-between" align="center">
                    <Text fontWeight="medium">Opportunity Score</Text>
                    <Badge colorScheme={scoreColor} size="lg" px={3} py={1}>
                      {score.normalizedScore}/100
                    </Badge>
                  </HStack>
                  
                  <Progress 
                    value={score.normalizedScore} 
                    colorScheme={scoreColor}
                    size="lg"
                    borderRadius="md"
                  />

                  {score.strengths.length > 0 && (
                    <VStack align="stretch" spacing={2}>
                      <Text fontWeight="medium" color="green.600">
                        Key Strengths
                      </Text>
                      <List spacing={1}>
                        {score.strengths.map((strength, idx) => (
                          <ListItem key={idx} fontSize="sm">
                            <ListIcon as={CheckCircleIcon} color="green.500" />
                            {strength}
                          </ListItem>
                        ))}
                      </List>
                    </VStack>
                  )}

                  {score.gaps.length > 0 && (
                    <VStack align="stretch" spacing={2}>
                      <Text fontWeight="medium" color="orange.600">
                        Areas for Improvement
                      </Text>
                      <List spacing={1}>
                        {score.gaps.map((gap, idx) => (
                          <ListItem key={idx} fontSize="sm">
                            <ListIcon as={WarningIcon} color="orange.500" />
                            {gap}
                          </ListItem>
                        ))}
                      </List>
                    </VStack>
                  )}
                </VStack>
              </Box>
            );
          })}
        </SimpleGrid>
      </VStack>

      <Box textAlign="center" pt={6}>
        <HStack justify="center" spacing={4}>
          <Button as={RouterLink} to="/" variant="outline">
            Try Another City
          </Button>
          <Button as={RouterLink} to="/rfp" colorScheme="green">
            Analyze RFP
          </Button>
        </HStack>
      </Box>
    </VStack>
  );
}