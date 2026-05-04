#!/bin/bash
# ============================================================
# E-commerce Prompt Workflow Demo
# ============================================================
# This script demonstrates a complete prompt engineering workflow
# Run: bash examples/ecommerce/workflow_demo.sh

set -e

echo "=========================================="
echo "  prompt-git E-commerce Workflow Demo"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create temporary workspace
WORKSPACE="/tmp/pg-ecommerce-demo"
rm -rf $WORKSPACE
mkdir -p $WORKSPACE
cd $WORKSPACE

echo -e "${GREEN}[1/7] Created workspace: $WORKSPACE${NC}"

# Initialize git repo
git init
git config user.name "Demo User"
git config user.email "demo@example.com"

echo -e "${GREEN}[2/7] Initialized git repository${NC}"

# Initialize prompt-git
pg init

echo -e "${GREEN}[3/7] Initialized prompt-git${NC}"

# Copy prompt files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/customer_service.yaml" .prompts/
cp "$SCRIPT_DIR/dataset.jsonl" .

echo -e "${GREEN}[4/7] Copied prompt and dataset files${NC}"

# Add and commit
pg add .prompts/customer_service.yaml
pg commit -m "Initial e-commerce customer service prompt"

echo -e "${GREEN}[5/7] Committed baseline prompt${NC}"

# Run baseline evaluation
echo ""
echo -e "${YELLOW}Running baseline evaluation...${NC}"
pg eval --dataset dataset.jsonl --threshold 0.05 --json > baseline.json

echo ""
echo "=========================================="
echo "  Baseline Results"
echo "=========================================="
python3 -c "
import json
with open('baseline.json') as f:
    data = json.load(f)
print(f'Samples: {data[\"total_samples\"]}')
print(f'Accuracy: {data[\"accuracy_old\"]:.1%}')
print(f'Consistency: {data[\"consistency_score\"]:.1%}')
"

# Simulate prompt improvement
echo ""
echo -e "${YELLOW}Simulating prompt improvement...${NC}"

cat > .prompts/customer_service_v2.yaml << 'EOF'
name: ecommerce-cs
version: "2.2.0"
system_prompt: |
  You are a senior customer service agent for ShopEasy, an e-commerce platform.
  
  Your primary responsibilities:
  1. Assist customers with order inquiries, returns, and product questions
  2. Resolve issues efficiently while maintaining customer satisfaction
  3. Escalate complex issues to human agents when necessary
  
  Communication guidelines:
  - Be polite, empathetic, and professional
  - Use clear and concise language
  - Acknowledge customer frustration before offering solutions
  - Never make promises you cannot keep
  
  Enhanced VIP handling:
  - Gold/Platinum members: Offer proactive solutions and priority queue
  - First-time buyers: Provide extra guidance and welcome discount info
  
  Policy reminders:
  - Returns accepted within 30 days of delivery
  - Refunds processed within 5-7 business days
  - Free shipping on orders over $50
  - VIP customers (Gold+) get priority support
  - Defective items: Free return shipping regardless of membership

user_template: |
  Customer Message: {{message}}
  
  Order Information:
  - Order ID: {{order_id}}
  - Order Status: {{order_status}}
  - Order Date: {{order_date}}
  - Items: {{items}}
  - Total: {{total_amount}}
  
  Customer Profile:
  - Name: {{customer_name}}
  - Membership: {{membership_tier}}
  - Previous Orders: {{order_count}}
  
  Context: {{context}}
  
  Please provide a helpful response addressing the customer's concern.

variables:
  message:
    type: string
    description: "Customer's original message"
  order_id:
    type: string
    description: "Order reference number"
    default: "N/A"
  order_status:
    type: string
    description: "Current order status"
    enum: ["pending", "processing", "shipped", "delivered", "cancelled", "returned"]
    default: "pending"
  order_date:
    type: string
    description: "Date when order was placed"
    default: "Unknown"
  items:
    type: string
    description: "List of items in the order"
    default: "[]"
  total_amount:
    type: string
    description: "Total order amount"
    default: "$0.00"
  customer_name:
    type: string
    description: "Customer's name"
    default: "Customer"
  membership_tier:
    type: string
    description: "Customer membership level"
    enum: ["standard", "silver", "gold", "platinum"]
    default: "standard"
  order_count:
    type: string
    description: "Number of previous orders"
    default: "0"
  context:
    type: string
    description: "Additional context for the interaction"
    default: "General inquiry"

constraints:
  - "Always verify order ID before providing order details"
  - "Never disclose internal pricing or profit margins"
  - "Offer alternatives before suggesting cancellation"
  - "For refunds over $100, escalate to supervisor"
  - "Response must be under 250 words"
  - "Include order ID in all responses for reference"
  - "If customer is upset, acknowledge frustration first"
  - "Never promise specific delivery dates without checking"
  - "For VIP customers (Gold+), offer expedited resolution"
  - "Suggest related products only after resolving the issue"
  - "For defective items, prioritize replacement over refund"
  - "Welcome first-time buyers with helpful tips"

metadata:
  author: support-team
  category: customer-service
  language: en
  max_tokens: 600
  temperature: 0.7
  tags: ["ecommerce", "support", "orders", "vip"]
EOF

# Show diff
echo ""
echo "=========================================="
echo "  Semantic Diff Analysis"
echo "=========================================="
cp .prompts/customer_service.yaml .prompts/customer_service_old.yaml
cp .prompts/customer_service_v2.yaml .prompts/customer_service.yaml

pg diff --semantic .prompts/customer_service.yaml

# Commit and evaluate
pg commit -m "v2.2: Enhanced VIP handling and context support"

echo ""
echo -e "${YELLOW}Running evaluation on improved prompt...${NC}"
pg eval --dataset dataset.jsonl --threshold 0.05 --json > v2.json

echo ""
echo "=========================================="
echo "  A/B Comparison"
echo "=========================================="
python3 << 'SCRIPT'
import json

with open('baseline.json') as f:
    v1 = json.load(f)
with open('v2.json') as f:
    v2 = json.load(f)

print(f"{'Metric':<20} {'V1':>10} {'V2':>10} {'Delta':>10}")
print("-" * 50)
print(f"{'Accuracy':<20} {v1['accuracy_old']:>10.1%} {v2['accuracy_new']:>10.1%} {v2['accuracy_delta']:>+10.1%}")
print(f"{'Token Cost':<20} {v1['token_cost_old']:>10} {v2['token_cost_new']:>10} {v2['token_cost_delta']:>+10.1%}")
print(f"{'Consistency':<20} {'N/A':>10} {v2['consistency_score']:>10.1%} {'N/A':>10}")
print("-" * 50)
print(f"{'Status':<20} {'':>10} {'PASSED' if v2['passed'] else 'FAILED':>10}")
SCRIPT

# Generate CI config
echo ""
echo -e "${YELLOW}Generating CI configuration...${NC}"
pg ci init --dry-run

echo ""
echo "=========================================="
echo "  Demo Complete!"
echo "=========================================="
echo ""
echo "Workspace: $WORKSPACE"
echo ""
echo "Next steps:"
echo "  1. cd $WORKSPACE"
echo "  2. pg diff --semantic"
echo "  3. pg eval --dataset dataset.jsonl"
echo ""
