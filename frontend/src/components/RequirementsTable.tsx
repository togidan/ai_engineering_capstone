import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Text,
  Box,
  useColorModeValue,
  Tooltip
} from '@chakra-ui/react';
import { RequirementRow } from '../lib/types';

interface RequirementsTableProps {
  requirements: RequirementRow[];
}

export default function RequirementsTable({ requirements }: RequirementsTableProps) {
  const tableBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  
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

  if (requirements.length === 0) {
    return (
      <Box textAlign="center" py={8}>
        <Text color="gray.500">No requirements found in the RFP</Text>
      </Box>
    );
  }

  return (
    <Box overflowX="auto" bg={tableBg} borderRadius="md" border="1px solid" borderColor={borderColor}>
      <Table variant="simple" size="sm">
        <Thead bg="gray.50">
          <Tr>
            <Th>Section</Th>
            <Th>Priority</Th>
            <Th>Requirement</Th>
            <Th>Answer</Th>
            <Th>Status</Th>
            <Th>Source</Th>
            <Th>Notes</Th>
          </Tr>
        </Thead>
        <Tbody>
          {requirements.map((req) => (
            <Tr key={req.id} _hover={{ bg: 'gray.50' }}>
              <Td>
                <Badge variant="outline" colorScheme="blue">
                  {req.section}
                </Badge>
              </Td>
              
              <Td>
                <Badge colorScheme={getPriorityColor(req.priority)} size="sm">
                  {req.priority}
                </Badge>
              </Td>
              
              <Td maxW="300px">
                <Tooltip label={req.requirement_text} placement="top">
                  <Text fontSize="sm" noOfLines={2}>
                    {req.requirement_text}
                  </Text>
                </Tooltip>
              </Td>
              
              <Td>
                <Text 
                  fontSize="sm" 
                  color={req.answer_value === 'TODO' ? 'orange.500' : 'inherit'}
                  fontWeight={req.answer_value === 'TODO' ? 'bold' : 'normal'}
                >
                  {req.answer_value || '-'}
                  {req.unit && req.answer_value !== 'TODO' && ` ${req.unit}`}
                </Text>
              </Td>
              
              <Td>
                <Badge colorScheme={getStatusColor(req.status)} size="sm">
                  {req.status.replace('_', ' ')}
                </Badge>
              </Td>
              
              <Td>
                <Text fontSize="sm" color="gray.600">
                  {req.source_field || '-'}
                </Text>
              </Td>
              
              <Td maxW="200px">
                {req.notes && (
                  <Tooltip label={req.notes} placement="top">
                    <Text fontSize="sm" color="gray.600" noOfLines={1}>
                      {req.notes}
                    </Text>
                  </Tooltip>
                )}
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
}