import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Divider,
  useColorModeValue,
  useToast,
  Heading
} from '@chakra-ui/react';
import { CopyIcon } from '@chakra-ui/icons';
import { DraftResponse } from '../lib/types';

interface DraftBoxProps {
  draft: DraftResponse;
}

export default function DraftBox({ draft }: DraftBoxProps) {
  const toast = useToast();
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  
  const handleCopy = async () => {
    const fullText = draft.sections
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

  const handleCopySection = async (section: { heading: string; content: string }) => {
    const sectionText = `${section.heading}\n\n${section.content}`;
    
    try {
      await navigator.clipboard.writeText(sectionText);
      toast({
        title: 'Section copied',
        description: `"${section.heading}" section copied to clipboard`,
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    } catch (err) {
      toast({
        title: 'Failed to copy',
        description: 'Could not copy section to clipboard',
        status: 'error',
        duration: 2000,
        isClosable: true,
      });
    }
  };

  return (
    <Box
      p={6}
      bg={cardBg}
      border="1px solid"
      borderColor={borderColor}
      borderRadius="lg"
      shadow="md"
    >
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between" align="center">
          <Heading size="md" color="green.600">
            RFI Draft Response
          </Heading>
          <Button
            leftIcon={<CopyIcon />}
            colorScheme="green"
            variant="outline"
            size="sm"
            onClick={handleCopy}
          >
            Copy All
          </Button>
        </HStack>

        <VStack spacing={6} align="stretch">
          {draft.sections.map((section, index) => (
            <Box key={index}>
              <HStack justify="space-between" align="center" mb={3}>
                <Heading size="sm" color="blue.600">
                  {section.heading}
                </Heading>
                <Button
                  leftIcon={<CopyIcon />}
                  size="xs"
                  variant="ghost"
                  onClick={() => handleCopySection(section)}
                >
                  Copy
                </Button>
              </HStack>
              
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
              
              {index < draft.sections.length - 1 && <Divider />}
            </Box>
          ))}
        </VStack>

        <Box pt={4} borderTop="1px solid" borderTopColor={borderColor}>
          <Text fontSize="xs" color="gray.500" textAlign="center">
            This is a draft response generated from your RFP analysis. 
            Please review and customize before submitting.
          </Text>
        </Box>
      </VStack>
    </Box>
  );
}