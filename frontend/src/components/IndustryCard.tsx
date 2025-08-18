import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Progress,
  List,
  ListItem,
  ListIcon,
  Button,
  useColorModeValue
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import { IndustryScore } from '../lib/types';

interface IndustryCardProps {
  industryScore: IndustryScore;
  onGeneratePitch?: () => void;
  rank?: number;
}

export default function IndustryCard({ 
  industryScore, 
  onGeneratePitch,
  rank 
}: IndustryCardProps) {
  const { industry, normalizedScore, strengths, gaps, details } = industryScore;
  
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'green';
    if (score >= 60) return 'yellow';
    return 'red';
  };

  const scoreColor = getScoreColor(normalizedScore);

  return (
    <Box
      p={6}
      bg={cardBg}
      border="1px solid"
      borderColor={borderColor}
      borderRadius="lg"
      shadow="md"
      position="relative"
    >
      {rank && (
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
          #{rank}
        </Badge>
      )}
      
      <VStack align="stretch" spacing={4}>
        <VStack align="stretch" spacing={2}>
          <Text fontSize="xl" fontWeight="bold" color={`${scoreColor}.600`}>
            {industry.name}
          </Text>
          <Text fontSize="sm" color="gray.600">
            {industry.description}
          </Text>
        </VStack>

        <HStack justify="space-between" align="center">
          <Text fontWeight="medium">Opportunity Score</Text>
          <Badge colorScheme={scoreColor} size="lg" px={3} py={1}>
            {normalizedScore}/100
          </Badge>
        </HStack>
        
        <Progress 
          value={normalizedScore} 
          colorScheme={scoreColor}
          size="lg"
          borderRadius="md"
        />

        {strengths.length > 0 && (
          <VStack align="stretch" spacing={2}>
            <Text fontWeight="medium" color="green.600">
              Key Strengths
            </Text>
            <List spacing={1}>
              {strengths.map((strength, index) => (
                <ListItem key={index} fontSize="sm">
                  <ListIcon as={CheckCircleIcon} color="green.500" />
                  {strength}
                </ListItem>
              ))}
            </List>
          </VStack>
        )}

        {gaps.length > 0 && (
          <VStack align="stretch" spacing={2}>
            <Text fontWeight="medium" color="orange.600">
              Areas for Improvement
            </Text>
            <List spacing={1}>
              {gaps.map((gap, index) => (
                <ListItem key={index} fontSize="sm">
                  <ListIcon as={WarningIcon} color="orange.500" />
                  {gap}
                </ListItem>
              ))}
            </List>
          </VStack>
        )}

        {Object.keys(details).length > 0 && (
          <VStack align="stretch" spacing={2}>
            <Text fontWeight="medium" color="blue.600">
              Scoring Details
            </Text>
            <Box fontSize="sm" color="gray.600">
              {Object.entries(details)
                .sort(([,a], [,b]) => b.normalized - a.normalized)
                .slice(0, 3)
                .map(([metric, data]) => (
                  <HStack key={metric} justify="space-between">
                    <Text>{metric.replace(/_/g, ' ')}</Text>
                    <Text>{Math.round(data.normalized * 100)}%</Text>
                  </HStack>
                ))}
            </Box>
          </VStack>
        )}

        {onGeneratePitch && (
          <Button
            colorScheme="blue"
            size="sm"
            onClick={onGeneratePitch}
            mt={2}
          >
            Generate Pitch
          </Button>
        )}
      </VStack>
    </Box>
  );
}