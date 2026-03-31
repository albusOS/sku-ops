export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      addresses: {
        Row: {
          billing_entity_id: string | null
          city: string
          country: string
          created_at: string
          id: string
          job_id: string | null
          label: string
          line1: string
          line2: string
          organization_id: string
          postal_code: string
          state: string
        }
        Insert: {
          billing_entity_id?: string | null
          city?: string
          country?: string
          created_at: string
          id: string
          job_id?: string | null
          label?: string
          line1?: string
          line2?: string
          organization_id: string
          postal_code?: string
          state?: string
        }
        Update: {
          billing_entity_id?: string | null
          city?: string
          country?: string
          created_at?: string
          id?: string
          job_id?: string | null
          label?: string
          line1?: string
          line2?: string
          organization_id?: string
          postal_code?: string
          state?: string
        }
        Relationships: [
          {
            foreignKeyName: "addresses_billing_entity_id_fkey"
            columns: ["billing_entity_id"]
            isOneToOne: false
            referencedRelation: "billing_entities"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "addresses_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      agent_runs: {
        Row: {
          agent_name: string
          attempts: number
          cost_usd: number
          created_at: string
          duration_ms: number
          error: string | null
          error_kind: string | null
          handoff_from: string | null
          id: string
          input_tokens: number
          mode: string | null
          model: string
          org_id: string
          output_tokens: number
          parent_run_id: string | null
          response_text: string | null
          session_id: string
          tool_calls: string
          user_id: string | null
          user_message: string | null
          validation_failures: string
          validation_passed: boolean | null
          validation_scores: string
        }
        Insert: {
          agent_name: string
          attempts?: number
          cost_usd?: number
          created_at: string
          duration_ms?: number
          error?: string | null
          error_kind?: string | null
          handoff_from?: string | null
          id: string
          input_tokens?: number
          mode?: string | null
          model: string
          org_id: string
          output_tokens?: number
          parent_run_id?: string | null
          response_text?: string | null
          session_id: string
          tool_calls?: string
          user_id?: string | null
          user_message?: string | null
          validation_failures?: string
          validation_passed?: boolean | null
          validation_scores?: string
        }
        Update: {
          agent_name?: string
          attempts?: number
          cost_usd?: number
          created_at?: string
          duration_ms?: number
          error?: string | null
          error_kind?: string | null
          handoff_from?: string | null
          id?: string
          input_tokens?: number
          mode?: string | null
          model?: string
          org_id?: string
          output_tokens?: number
          parent_run_id?: string | null
          response_text?: string | null
          session_id?: string
          tool_calls?: string
          user_id?: string | null
          user_message?: string | null
          validation_failures?: string
          validation_passed?: boolean | null
          validation_scores?: string
        }
        Relationships: [
          {
            foreignKeyName: "agent_runs_org_id_fkey"
            columns: ["org_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "agent_runs_parent_run_id_fkey"
            columns: ["parent_run_id"]
            isOneToOne: false
            referencedRelation: "agent_runs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "agent_runs_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      audit_log: {
        Row: {
          action: string
          created_at: string
          details: string | null
          id: string
          ip_address: string | null
          organization_id: string | null
          resource_id: string | null
          resource_type: string | null
          user_id: string | null
        }
        Insert: {
          action: string
          created_at: string
          details?: string | null
          id: string
          ip_address?: string | null
          organization_id?: string | null
          resource_id?: string | null
          resource_type?: string | null
          user_id?: string | null
        }
        Update: {
          action?: string
          created_at?: string
          details?: string | null
          id?: string
          ip_address?: string | null
          organization_id?: string | null
          resource_id?: string | null
          resource_type?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "audit_log_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "audit_log_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      billing_entities: {
        Row: {
          billing_address: string
          contact_email: string
          contact_name: string
          created_at: string
          id: string
          is_active: boolean
          name: string
          organization_id: string
          payment_terms: string
          updated_at: string
          xero_contact_id: string | null
        }
        Insert: {
          billing_address?: string
          contact_email?: string
          contact_name?: string
          created_at: string
          id: string
          is_active?: boolean
          name: string
          organization_id: string
          payment_terms?: string
          updated_at: string
          xero_contact_id?: string | null
        }
        Update: {
          billing_address?: string
          contact_email?: string
          contact_name?: string
          created_at?: string
          id?: string
          is_active?: boolean
          name?: string
          organization_id?: string
          payment_terms?: string
          updated_at?: string
          xero_contact_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "billing_entities_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      credit_note_line_items: {
        Row: {
          amount: number
          cost: number
          credit_note_id: string
          description: string
          id: string
          quantity: number
          sell_cost: number
          sku_id: string | null
          unit: string
          unit_price: number
        }
        Insert: {
          amount: number
          cost?: number
          credit_note_id: string
          description?: string
          id: string
          quantity: number
          sell_cost?: number
          sku_id?: string | null
          unit?: string
          unit_price: number
        }
        Update: {
          amount?: number
          cost?: number
          credit_note_id?: string
          description?: string
          id?: string
          quantity?: number
          sell_cost?: number
          sku_id?: string | null
          unit?: string
          unit_price?: number
        }
        Relationships: [
          {
            foreignKeyName: "credit_note_line_items_credit_note_id_fkey"
            columns: ["credit_note_id"]
            isOneToOne: false
            referencedRelation: "credit_notes"
            referencedColumns: ["id"]
          },
        ]
      }
      credit_notes: {
        Row: {
          billing_entity: string
          billing_entity_id: string | null
          created_at: string
          credit_note_number: string
          id: string
          invoice_id: string | null
          notes: string | null
          organization_id: string | null
          return_id: string | null
          status: string
          subtotal: number
          tax: number
          total: number
          updated_at: string
          xero_credit_note_id: string | null
          xero_sync_status: string
        }
        Insert: {
          billing_entity?: string
          billing_entity_id?: string | null
          created_at: string
          credit_note_number: string
          id: string
          invoice_id?: string | null
          notes?: string | null
          organization_id?: string | null
          return_id?: string | null
          status?: string
          subtotal?: number
          tax?: number
          total?: number
          updated_at: string
          xero_credit_note_id?: string | null
          xero_sync_status?: string
        }
        Update: {
          billing_entity?: string
          billing_entity_id?: string | null
          created_at?: string
          credit_note_number?: string
          id?: string
          invoice_id?: string | null
          notes?: string | null
          organization_id?: string | null
          return_id?: string | null
          status?: string
          subtotal?: number
          tax?: number
          total?: number
          updated_at?: string
          xero_credit_note_id?: string | null
          xero_sync_status?: string
        }
        Relationships: [
          {
            foreignKeyName: "credit_notes_billing_entity_id_fkey"
            columns: ["billing_entity_id"]
            isOneToOne: false
            referencedRelation: "billing_entities"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "credit_notes_invoice_id_fkey"
            columns: ["invoice_id"]
            isOneToOne: false
            referencedRelation: "invoices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "credit_notes_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      cycle_count_items: {
        Row: {
          counted_qty: number | null
          created_at: string
          cycle_count_id: string
          id: string
          notes: string | null
          product_name: string
          sku: string
          sku_id: string
          snapshot_qty: number
          unit: string
          variance: number | null
        }
        Insert: {
          counted_qty?: number | null
          created_at: string
          cycle_count_id: string
          id: string
          notes?: string | null
          product_name?: string
          sku: string
          sku_id: string
          snapshot_qty: number
          unit?: string
          variance?: number | null
        }
        Update: {
          counted_qty?: number | null
          created_at?: string
          cycle_count_id?: string
          id?: string
          notes?: string | null
          product_name?: string
          sku?: string
          sku_id?: string
          snapshot_qty?: number
          unit?: string
          variance?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "cycle_count_items_cycle_count_id_fkey"
            columns: ["cycle_count_id"]
            isOneToOne: false
            referencedRelation: "cycle_counts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "cycle_count_items_sku_id_fkey"
            columns: ["sku_id"]
            isOneToOne: false
            referencedRelation: "skus"
            referencedColumns: ["id"]
          },
        ]
      }
      cycle_counts: {
        Row: {
          committed_at: string | null
          committed_by_id: string | null
          created_at: string
          created_by_id: string
          created_by_name: string
          id: string
          organization_id: string
          scope: string | null
          status: string
        }
        Insert: {
          committed_at?: string | null
          committed_by_id?: string | null
          created_at: string
          created_by_id: string
          created_by_name?: string
          id: string
          organization_id: string
          scope?: string | null
          status?: string
        }
        Update: {
          committed_at?: string | null
          committed_by_id?: string | null
          created_at?: string
          created_by_id?: string
          created_by_name?: string
          id?: string
          organization_id?: string
          scope?: string | null
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "cycle_counts_committed_by_id_fkey"
            columns: ["committed_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "cycle_counts_created_by_id_fkey"
            columns: ["created_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "cycle_counts_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      departments: {
        Row: {
          code: string
          created_at: string
          deleted_at: string | null
          description: string
          id: string
          name: string
          organization_id: string | null
          sku_count: number
        }
        Insert: {
          code: string
          created_at: string
          deleted_at?: string | null
          description?: string
          id: string
          name: string
          organization_id?: string | null
          sku_count?: number
        }
        Update: {
          code?: string
          created_at?: string
          deleted_at?: string | null
          description?: string
          id?: string
          name?: string
          organization_id?: string | null
          sku_count?: number
        }
        Relationships: [
          {
            foreignKeyName: "departments_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      documents: {
        Row: {
          created_at: string
          document_type: string
          file_hash: string
          file_size: number
          filename: string
          id: string
          mime_type: string
          organization_id: string
          parsed_data: string | null
          po_id: string | null
          status: string
          updated_at: string
          uploaded_by_id: string
          vendor_name: string | null
        }
        Insert: {
          created_at: string
          document_type?: string
          file_hash?: string
          file_size?: number
          filename: string
          id: string
          mime_type?: string
          organization_id: string
          parsed_data?: string | null
          po_id?: string | null
          status?: string
          updated_at: string
          uploaded_by_id: string
          vendor_name?: string | null
        }
        Update: {
          created_at?: string
          document_type?: string
          file_hash?: string
          file_size?: number
          filename?: string
          id?: string
          mime_type?: string
          organization_id?: string
          parsed_data?: string | null
          po_id?: string | null
          status?: string
          updated_at?: string
          uploaded_by_id?: string
          vendor_name?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "documents_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "documents_po_id_fkey"
            columns: ["po_id"]
            isOneToOne: false
            referencedRelation: "purchase_orders"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "documents_uploaded_by_id_fkey"
            columns: ["uploaded_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      embeddings: {
        Row: {
          content: string
          content_hash: string
          embedding: string
          entity_id: string
          entity_type: string
          id: string
          org_id: string
          updated_at: string
        }
        Insert: {
          content: string
          content_hash: string
          embedding: string
          entity_id: string
          entity_type: string
          id: string
          org_id: string
          updated_at: string
        }
        Update: {
          content?: string
          content_hash?: string
          embedding?: string
          entity_id?: string
          entity_type?: string
          id?: string
          org_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "embeddings_org_id_fkey"
            columns: ["org_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      financial_ledger: {
        Row: {
          account: string
          amount: number
          billing_entity: string | null
          billing_entity_id: string | null
          contractor_id: string | null
          created_at: string
          department: string | null
          id: string
          job_id: string | null
          journal_id: string | null
          organization_id: string | null
          performed_by_user_id: string | null
          quantity: number | null
          reference_id: string
          reference_type: string
          sku_id: string | null
          unit: string | null
          unit_cost: number | null
          vendor_name: string | null
        }
        Insert: {
          account: string
          amount: number
          billing_entity?: string | null
          billing_entity_id?: string | null
          contractor_id?: string | null
          created_at: string
          department?: string | null
          id: string
          job_id?: string | null
          journal_id?: string | null
          organization_id?: string | null
          performed_by_user_id?: string | null
          quantity?: number | null
          reference_id: string
          reference_type: string
          sku_id?: string | null
          unit?: string | null
          unit_cost?: number | null
          vendor_name?: string | null
        }
        Update: {
          account?: string
          amount?: number
          billing_entity?: string | null
          billing_entity_id?: string | null
          contractor_id?: string | null
          created_at?: string
          department?: string | null
          id?: string
          job_id?: string | null
          journal_id?: string | null
          organization_id?: string | null
          performed_by_user_id?: string | null
          quantity?: number | null
          reference_id?: string
          reference_type?: string
          sku_id?: string | null
          unit?: string | null
          unit_cost?: number | null
          vendor_name?: string | null
        }
        Relationships: []
      }
      fiscal_periods: {
        Row: {
          closed_at: string | null
          closed_by_id: string | null
          created_at: string
          end_date: string
          id: string
          name: string
          organization_id: string
          start_date: string
          status: string
        }
        Insert: {
          closed_at?: string | null
          closed_by_id?: string | null
          created_at: string
          end_date: string
          id: string
          name: string
          organization_id: string
          start_date: string
          status?: string
        }
        Update: {
          closed_at?: string | null
          closed_by_id?: string | null
          created_at?: string
          end_date?: string
          id?: string
          name?: string
          organization_id?: string
          start_date?: string
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "fiscal_periods_closed_by_id_fkey"
            columns: ["closed_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "fiscal_periods_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      invoice_counters: {
        Row: {
          counter: number
          key: string
          organization_id: string
        }
        Insert: {
          counter?: number
          key: string
          organization_id: string
        }
        Update: {
          counter?: number
          key?: string
          organization_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "invoice_counters_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      invoice_line_items: {
        Row: {
          amount: number
          cost: number
          description: string
          id: string
          invoice_id: string
          job_id: string | null
          quantity: number
          sell_cost: number
          sku_id: string | null
          unit: string
          unit_price: number
        }
        Insert: {
          amount: number
          cost?: number
          description?: string
          id: string
          invoice_id: string
          job_id?: string | null
          quantity: number
          sell_cost?: number
          sku_id?: string | null
          unit?: string
          unit_price: number
        }
        Update: {
          amount?: number
          cost?: number
          description?: string
          id?: string
          invoice_id?: string
          job_id?: string | null
          quantity?: number
          sell_cost?: number
          sku_id?: string | null
          unit?: string
          unit_price?: number
        }
        Relationships: [
          {
            foreignKeyName: "invoice_line_items_invoice_id_fkey"
            columns: ["invoice_id"]
            isOneToOne: false
            referencedRelation: "invoices"
            referencedColumns: ["id"]
          },
        ]
      }
      invoice_withdrawals: {
        Row: {
          invoice_id: string
          withdrawal_id: string
        }
        Insert: {
          invoice_id: string
          withdrawal_id: string
        }
        Update: {
          invoice_id?: string
          withdrawal_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "invoice_withdrawals_invoice_id_fkey"
            columns: ["invoice_id"]
            isOneToOne: false
            referencedRelation: "invoices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "invoice_withdrawals_withdrawal_id_fkey"
            columns: ["withdrawal_id"]
            isOneToOne: false
            referencedRelation: "withdrawals"
            referencedColumns: ["id"]
          },
        ]
      }
      invoices: {
        Row: {
          amount_credited: number
          approved_at: string | null
          approved_by_id: string | null
          billing_address: string
          billing_entity: string
          billing_entity_id: string | null
          contact_email: string
          contact_name: string
          created_at: string
          currency: string
          deleted_at: string | null
          due_date: string | null
          id: string
          invoice_date: string | null
          invoice_number: string
          notes: string | null
          organization_id: string | null
          payment_terms: string
          po_reference: string
          status: string
          subtotal: number
          tax: number
          tax_rate: number
          total: number
          updated_at: string
          xero_cogs_journal_id: string | null
          xero_invoice_id: string | null
          xero_sync_status: string
        }
        Insert: {
          amount_credited?: number
          approved_at?: string | null
          approved_by_id?: string | null
          billing_address?: string
          billing_entity?: string
          billing_entity_id?: string | null
          contact_email?: string
          contact_name?: string
          created_at: string
          currency?: string
          deleted_at?: string | null
          due_date?: string | null
          id: string
          invoice_date?: string | null
          invoice_number: string
          notes?: string | null
          organization_id?: string | null
          payment_terms?: string
          po_reference?: string
          status?: string
          subtotal: number
          tax: number
          tax_rate?: number
          total: number
          updated_at: string
          xero_cogs_journal_id?: string | null
          xero_invoice_id?: string | null
          xero_sync_status?: string
        }
        Update: {
          amount_credited?: number
          approved_at?: string | null
          approved_by_id?: string | null
          billing_address?: string
          billing_entity?: string
          billing_entity_id?: string | null
          contact_email?: string
          contact_name?: string
          created_at?: string
          currency?: string
          deleted_at?: string | null
          due_date?: string | null
          id?: string
          invoice_date?: string | null
          invoice_number?: string
          notes?: string | null
          organization_id?: string | null
          payment_terms?: string
          po_reference?: string
          status?: string
          subtotal?: number
          tax?: number
          tax_rate?: number
          total?: number
          updated_at?: string
          xero_cogs_journal_id?: string | null
          xero_invoice_id?: string | null
          xero_sync_status?: string
        }
        Relationships: [
          {
            foreignKeyName: "invoices_approved_by_id_fkey"
            columns: ["approved_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "invoices_billing_entity_id_fkey"
            columns: ["billing_entity_id"]
            isOneToOne: false
            referencedRelation: "billing_entities"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "invoices_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      jobs: {
        Row: {
          billing_entity_id: string | null
          code: string
          created_at: string
          id: string
          name: string
          notes: string | null
          organization_id: string
          service_address: string
          status: string
          updated_at: string
        }
        Insert: {
          billing_entity_id?: string | null
          code: string
          created_at: string
          id: string
          name?: string
          notes?: string | null
          organization_id: string
          service_address?: string
          status?: string
          updated_at: string
        }
        Update: {
          billing_entity_id?: string | null
          code?: string
          created_at?: string
          id?: string
          name?: string
          notes?: string | null
          organization_id?: string
          service_address?: string
          status?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "jobs_billing_entity_id_fkey"
            columns: ["billing_entity_id"]
            isOneToOne: false
            referencedRelation: "billing_entities"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "jobs_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      material_request_items: {
        Row: {
          cost: number
          id: string
          material_request_id: string
          name: string
          quantity: number
          sku: string
          sku_id: string
          unit: string
          unit_price: number
        }
        Insert: {
          cost?: number
          id: string
          material_request_id: string
          name?: string
          quantity: number
          sku?: string
          sku_id: string
          unit?: string
          unit_price?: number
        }
        Update: {
          cost?: number
          id?: string
          material_request_id?: string
          name?: string
          quantity?: number
          sku?: string
          sku_id?: string
          unit?: string
          unit_price?: number
        }
        Relationships: [
          {
            foreignKeyName: "material_request_items_material_request_id_fkey"
            columns: ["material_request_id"]
            isOneToOne: false
            referencedRelation: "material_requests"
            referencedColumns: ["id"]
          },
        ]
      }
      material_requests: {
        Row: {
          contractor_id: string
          contractor_name: string
          created_at: string
          id: string
          job_id: string | null
          notes: string | null
          organization_id: string
          processed_at: string | null
          processed_by_id: string | null
          service_address: string | null
          status: string
          withdrawal_id: string | null
        }
        Insert: {
          contractor_id: string
          contractor_name?: string
          created_at: string
          id: string
          job_id?: string | null
          notes?: string | null
          organization_id: string
          processed_at?: string | null
          processed_by_id?: string | null
          service_address?: string | null
          status?: string
          withdrawal_id?: string | null
        }
        Update: {
          contractor_id?: string
          contractor_name?: string
          created_at?: string
          id?: string
          job_id?: string | null
          notes?: string | null
          organization_id?: string
          processed_at?: string | null
          processed_by_id?: string | null
          service_address?: string | null
          status?: string
          withdrawal_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "material_requests_contractor_id_fkey"
            columns: ["contractor_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "material_requests_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "material_requests_processed_by_id_fkey"
            columns: ["processed_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "material_requests_withdrawal_id_fkey"
            columns: ["withdrawal_id"]
            isOneToOne: false
            referencedRelation: "withdrawals"
            referencedColumns: ["id"]
          },
        ]
      }
      memory_artifacts: {
        Row: {
          content: string
          created_at: string
          expires_at: string | null
          id: string
          org_id: string
          session_id: string
          subject: string
          tags: string
          type: string
          user_id: string
        }
        Insert: {
          content?: string
          created_at: string
          expires_at?: string | null
          id: string
          org_id: string
          session_id: string
          subject?: string
          tags?: string
          type?: string
          user_id: string
        }
        Update: {
          content?: string
          created_at?: string
          expires_at?: string | null
          id?: string
          org_id?: string
          session_id?: string
          subject?: string
          tags?: string
          type?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "memory_artifacts_org_id_fkey"
            columns: ["org_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "memory_artifacts_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      oauth_states: {
        Row: {
          created_at: string
          org_id: string
          state: string
        }
        Insert: {
          created_at: string
          org_id: string
          state: string
        }
        Update: {
          created_at?: string
          org_id?: string
          state?: string
        }
        Relationships: [
          {
            foreignKeyName: "oauth_states_org_id_fkey"
            columns: ["org_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      org_settings: {
        Row: {
          auto_invoice: boolean
          default_tax_rate: number
          organization_id: string
          updated_at: string | null
          xero_access_token: string | null
          xero_ap_account_code: string
          xero_cogs_account_code: string
          xero_inventory_account_code: string
          xero_refresh_token: string | null
          xero_sales_account_code: string
          xero_tax_type: string
          xero_tenant_id: string | null
          xero_token_expiry: string | null
          xero_tracking_category_id: string | null
        }
        Insert: {
          auto_invoice?: boolean
          default_tax_rate?: number
          organization_id: string
          updated_at?: string | null
          xero_access_token?: string | null
          xero_ap_account_code?: string
          xero_cogs_account_code?: string
          xero_inventory_account_code?: string
          xero_refresh_token?: string | null
          xero_sales_account_code?: string
          xero_tax_type?: string
          xero_tenant_id?: string | null
          xero_token_expiry?: string | null
          xero_tracking_category_id?: string | null
        }
        Update: {
          auto_invoice?: boolean
          default_tax_rate?: number
          organization_id?: string
          updated_at?: string | null
          xero_access_token?: string | null
          xero_ap_account_code?: string
          xero_cogs_account_code?: string
          xero_inventory_account_code?: string
          xero_refresh_token?: string | null
          xero_sales_account_code?: string
          xero_tax_type?: string
          xero_tenant_id?: string | null
          xero_token_expiry?: string | null
          xero_tracking_category_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "org_settings_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: true
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      organizations: {
        Row: {
          created_at: string
          id: string
          name: string
          slug: string
        }
        Insert: {
          created_at: string
          id: string
          name: string
          slug: string
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
          slug?: string
        }
        Relationships: []
      }
      payment_withdrawals: {
        Row: {
          payment_id: string
          withdrawal_id: string
        }
        Insert: {
          payment_id: string
          withdrawal_id: string
        }
        Update: {
          payment_id?: string
          withdrawal_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "payment_withdrawals_payment_id_fkey"
            columns: ["payment_id"]
            isOneToOne: false
            referencedRelation: "payments"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "payment_withdrawals_withdrawal_id_fkey"
            columns: ["withdrawal_id"]
            isOneToOne: false
            referencedRelation: "withdrawals"
            referencedColumns: ["id"]
          },
        ]
      }
      payments: {
        Row: {
          amount: number
          billing_entity_id: string | null
          created_at: string
          id: string
          invoice_id: string | null
          method: string
          notes: string | null
          organization_id: string
          payment_date: string
          recorded_by_id: string
          reference: string
          updated_at: string
          xero_payment_id: string | null
        }
        Insert: {
          amount: number
          billing_entity_id?: string | null
          created_at: string
          id: string
          invoice_id?: string | null
          method?: string
          notes?: string | null
          organization_id: string
          payment_date: string
          recorded_by_id: string
          reference?: string
          updated_at: string
          xero_payment_id?: string | null
        }
        Update: {
          amount?: number
          billing_entity_id?: string | null
          created_at?: string
          id?: string
          invoice_id?: string | null
          method?: string
          notes?: string | null
          organization_id?: string
          payment_date?: string
          recorded_by_id?: string
          reference?: string
          updated_at?: string
          xero_payment_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "payments_billing_entity_id_fkey"
            columns: ["billing_entity_id"]
            isOneToOne: false
            referencedRelation: "billing_entities"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "payments_invoice_id_fkey"
            columns: ["invoice_id"]
            isOneToOne: false
            referencedRelation: "invoices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "payments_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "payments_recorded_by_id_fkey"
            columns: ["recorded_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      processed_events: {
        Row: {
          event_id: string
          event_type: string
          handler_name: string
          processed_at: string
        }
        Insert: {
          event_id: string
          event_type: string
          handler_name: string
          processed_at: string
        }
        Update: {
          event_id?: string
          event_type?: string
          handler_name?: string
          processed_at?: string
        }
        Relationships: []
      }
      products: {
        Row: {
          category_id: string
          category_name: string
          created_at: string
          deleted_at: string | null
          description: string
          id: string
          name: string
          organization_id: string | null
          sku_count: number
          updated_at: string
        }
        Insert: {
          category_id: string
          category_name?: string
          created_at: string
          deleted_at?: string | null
          description?: string
          id: string
          name: string
          organization_id?: string | null
          sku_count?: number
          updated_at: string
        }
        Update: {
          category_id?: string
          category_name?: string
          created_at?: string
          deleted_at?: string | null
          description?: string
          id?: string
          name?: string
          organization_id?: string | null
          sku_count?: number
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "products_category_id_fkey"
            columns: ["category_id"]
            isOneToOne: false
            referencedRelation: "departments"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "products_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      purchase_order_items: {
        Row: {
          base_unit: string
          cost: number
          delivered_qty: number | null
          id: string
          name: string
          ordered_qty: number
          organization_id: string | null
          original_sku: string | null
          pack_qty: number
          po_id: string
          purchase_pack_qty: number
          purchase_uom: string
          sell_uom: string
          sku_id: string | null
          status: string
          suggested_department: string
          unit_price: number
        }
        Insert: {
          base_unit?: string
          cost?: number
          delivered_qty?: number | null
          id: string
          name: string
          ordered_qty?: number
          organization_id?: string | null
          original_sku?: string | null
          pack_qty?: number
          po_id: string
          purchase_pack_qty?: number
          purchase_uom?: string
          sell_uom?: string
          sku_id?: string | null
          status?: string
          suggested_department?: string
          unit_price?: number
        }
        Update: {
          base_unit?: string
          cost?: number
          delivered_qty?: number | null
          id?: string
          name?: string
          ordered_qty?: number
          organization_id?: string | null
          original_sku?: string | null
          pack_qty?: number
          po_id?: string
          purchase_pack_qty?: number
          purchase_uom?: string
          sell_uom?: string
          sku_id?: string | null
          status?: string
          suggested_department?: string
          unit_price?: number
        }
        Relationships: [
          {
            foreignKeyName: "purchase_order_items_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "purchase_order_items_po_id_fkey"
            columns: ["po_id"]
            isOneToOne: false
            referencedRelation: "purchase_orders"
            referencedColumns: ["id"]
          },
        ]
      }
      purchase_orders: {
        Row: {
          created_at: string
          created_by_id: string
          created_by_name: string
          document_date: string | null
          document_id: string | null
          id: string
          notes: string | null
          organization_id: string | null
          received_at: string | null
          received_by_id: string | null
          received_by_name: string | null
          status: string
          total: number | null
          updated_at: string | null
          vendor_id: string | null
          vendor_name: string
          xero_bill_id: string | null
          xero_sync_status: string
        }
        Insert: {
          created_at: string
          created_by_id: string
          created_by_name?: string
          document_date?: string | null
          document_id?: string | null
          id: string
          notes?: string | null
          organization_id?: string | null
          received_at?: string | null
          received_by_id?: string | null
          received_by_name?: string | null
          status?: string
          total?: number | null
          updated_at?: string | null
          vendor_id?: string | null
          vendor_name?: string
          xero_bill_id?: string | null
          xero_sync_status?: string
        }
        Update: {
          created_at?: string
          created_by_id?: string
          created_by_name?: string
          document_date?: string | null
          document_id?: string | null
          id?: string
          notes?: string | null
          organization_id?: string | null
          received_at?: string | null
          received_by_id?: string | null
          received_by_name?: string | null
          status?: string
          total?: number | null
          updated_at?: string | null
          vendor_id?: string | null
          vendor_name?: string
          xero_bill_id?: string | null
          xero_sync_status?: string
        }
        Relationships: [
          {
            foreignKeyName: "purchase_orders_created_by_id_fkey"
            columns: ["created_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "purchase_orders_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "purchase_orders_received_by_id_fkey"
            columns: ["received_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "purchase_orders_vendor_id_fkey"
            columns: ["vendor_id"]
            isOneToOne: false
            referencedRelation: "vendors"
            referencedColumns: ["id"]
          },
        ]
      }
      refresh_tokens: {
        Row: {
          created_at: string
          expires_at: string
          id: string
          revoked: boolean
          token_hash: string
          user_id: string
        }
        Insert: {
          created_at: string
          expires_at: string
          id: string
          revoked?: boolean
          token_hash: string
          user_id: string
        }
        Update: {
          created_at?: string
          expires_at?: string
          id?: string
          revoked?: boolean
          token_hash?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "refresh_tokens_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      return_items: {
        Row: {
          amount: number
          cost: number
          cost_total: number
          id: string
          name: string
          quantity: number
          return_id: string
          sell_cost: number
          sell_uom: string
          sku: string
          sku_id: string
          unit: string
          unit_price: number
        }
        Insert: {
          amount?: number
          cost?: number
          cost_total?: number
          id: string
          name?: string
          quantity: number
          return_id: string
          sell_cost?: number
          sell_uom?: string
          sku?: string
          sku_id: string
          unit?: string
          unit_price?: number
        }
        Update: {
          amount?: number
          cost?: number
          cost_total?: number
          id?: string
          name?: string
          quantity?: number
          return_id?: string
          sell_cost?: number
          sell_uom?: string
          sku?: string
          sku_id?: string
          unit?: string
          unit_price?: number
        }
        Relationships: [
          {
            foreignKeyName: "return_items_return_id_fkey"
            columns: ["return_id"]
            isOneToOne: false
            referencedRelation: "returns"
            referencedColumns: ["id"]
          },
        ]
      }
      returns: {
        Row: {
          billing_entity: string
          billing_entity_id: string | null
          contractor_id: string
          contractor_name: string
          cost_total: number
          created_at: string
          credit_note_id: string | null
          id: string
          job_id: string
          notes: string | null
          organization_id: string | null
          processed_by_id: string
          processed_by_name: string
          reason: string
          subtotal: number
          tax: number
          total: number
          updated_at: string
          withdrawal_id: string
        }
        Insert: {
          billing_entity?: string
          billing_entity_id?: string | null
          contractor_id: string
          contractor_name?: string
          cost_total?: number
          created_at: string
          credit_note_id?: string | null
          id: string
          job_id: string
          notes?: string | null
          organization_id?: string | null
          processed_by_id: string
          processed_by_name?: string
          reason?: string
          subtotal?: number
          tax?: number
          total?: number
          updated_at: string
          withdrawal_id: string
        }
        Update: {
          billing_entity?: string
          billing_entity_id?: string | null
          contractor_id?: string
          contractor_name?: string
          cost_total?: number
          created_at?: string
          credit_note_id?: string | null
          id?: string
          job_id?: string
          notes?: string | null
          organization_id?: string | null
          processed_by_id?: string
          processed_by_name?: string
          reason?: string
          subtotal?: number
          tax?: number
          total?: number
          updated_at?: string
          withdrawal_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "returns_billing_entity_id_fkey"
            columns: ["billing_entity_id"]
            isOneToOne: false
            referencedRelation: "billing_entities"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "returns_contractor_id_fkey"
            columns: ["contractor_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "returns_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "returns_processed_by_id_fkey"
            columns: ["processed_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "returns_withdrawal_id_fkey"
            columns: ["withdrawal_id"]
            isOneToOne: false
            referencedRelation: "withdrawals"
            referencedColumns: ["id"]
          },
        ]
      }
      sku_counters: {
        Row: {
          counter: number
          organization_id: string
          product_family_id: string
        }
        Insert: {
          counter?: number
          organization_id: string
          product_family_id: string
        }
        Update: {
          counter?: number
          organization_id?: string
          product_family_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "sku_counters_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "sku_counters_product_family_id_fkey"
            columns: ["product_family_id"]
            isOneToOne: false
            referencedRelation: "products"
            referencedColumns: ["id"]
          },
        ]
      }
      skus: {
        Row: {
          barcode: string | null
          base_unit: string
          category_id: string
          category_name: string
          cost: number
          created_at: string
          deleted_at: string | null
          description: string
          grade: string
          id: string
          min_stock: number
          name: string
          organization_id: string | null
          pack_qty: number
          price: number
          product_family_id: string
          purchase_pack_qty: number
          purchase_uom: string
          quantity: number
          sell_uom: string
          sku: string
          spec: string
          updated_at: string
          variant_attrs: string
          variant_label: string
          vendor_barcode: string | null
        }
        Insert: {
          barcode?: string | null
          base_unit?: string
          category_id: string
          category_name?: string
          cost?: number
          created_at: string
          deleted_at?: string | null
          description?: string
          grade?: string
          id: string
          min_stock?: number
          name: string
          organization_id?: string | null
          pack_qty?: number
          price: number
          product_family_id: string
          purchase_pack_qty?: number
          purchase_uom?: string
          quantity?: number
          sell_uom?: string
          sku: string
          spec?: string
          updated_at: string
          variant_attrs?: string
          variant_label?: string
          vendor_barcode?: string | null
        }
        Update: {
          barcode?: string | null
          base_unit?: string
          category_id?: string
          category_name?: string
          cost?: number
          created_at?: string
          deleted_at?: string | null
          description?: string
          grade?: string
          id?: string
          min_stock?: number
          name?: string
          organization_id?: string | null
          pack_qty?: number
          price?: number
          product_family_id?: string
          purchase_pack_qty?: number
          purchase_uom?: string
          quantity?: number
          sell_uom?: string
          sku?: string
          spec?: string
          updated_at?: string
          variant_attrs?: string
          variant_label?: string
          vendor_barcode?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "skus_category_id_fkey"
            columns: ["category_id"]
            isOneToOne: false
            referencedRelation: "departments"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "skus_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "skus_product_family_id_fkey"
            columns: ["product_family_id"]
            isOneToOne: false
            referencedRelation: "products"
            referencedColumns: ["id"]
          },
        ]
      }
      stock_transactions: {
        Row: {
          created_at: string
          id: string
          organization_id: string
          original_quantity: number | null
          original_unit: string | null
          product_name: string
          quantity_after: number
          quantity_before: number
          quantity_delta: number
          reason: string | null
          reference_id: string | null
          reference_type: string | null
          sku: string
          sku_id: string
          transaction_type: string
          unit: string
          user_id: string
          user_name: string
        }
        Insert: {
          created_at: string
          id: string
          organization_id: string
          original_quantity?: number | null
          original_unit?: string | null
          product_name?: string
          quantity_after: number
          quantity_before: number
          quantity_delta: number
          reason?: string | null
          reference_id?: string | null
          reference_type?: string | null
          sku: string
          sku_id: string
          transaction_type: string
          unit?: string
          user_id: string
          user_name?: string
        }
        Update: {
          created_at?: string
          id?: string
          organization_id?: string
          original_quantity?: number | null
          original_unit?: string | null
          product_name?: string
          quantity_after?: number
          quantity_before?: number
          quantity_delta?: number
          reason?: string | null
          reference_id?: string | null
          reference_type?: string | null
          sku?: string
          sku_id?: string
          transaction_type?: string
          unit?: string
          user_id?: string
          user_name?: string
        }
        Relationships: [
          {
            foreignKeyName: "stock_transactions_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "stock_transactions_sku_id_fkey"
            columns: ["sku_id"]
            isOneToOne: false
            referencedRelation: "skus"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "stock_transactions_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      units_of_measure: {
        Row: {
          code: string
          created_at: string
          deleted_at: string | null
          family: string
          id: string
          name: string
          organization_id: string | null
        }
        Insert: {
          code: string
          created_at: string
          deleted_at?: string | null
          family?: string
          id: string
          name: string
          organization_id?: string | null
        }
        Update: {
          code?: string
          created_at?: string
          deleted_at?: string | null
          family?: string
          id?: string
          name?: string
          organization_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "units_of_measure_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      users: {
        Row: {
          billing_entity: string | null
          billing_entity_id: string | null
          company: string | null
          created_at: string
          email: string
          id: string
          is_active: boolean
          name: string
          organization_id: string | null
          password: string
          phone: string | null
          role: string
        }
        Insert: {
          billing_entity?: string | null
          billing_entity_id?: string | null
          company?: string | null
          created_at: string
          email: string
          id: string
          is_active?: boolean
          name: string
          organization_id?: string | null
          password: string
          phone?: string | null
          role?: string
        }
        Update: {
          billing_entity?: string | null
          billing_entity_id?: string | null
          company?: string | null
          created_at?: string
          email?: string
          id?: string
          is_active?: boolean
          name?: string
          organization_id?: string | null
          password?: string
          phone?: string | null
          role?: string
        }
        Relationships: [
          {
            foreignKeyName: "users_billing_entity_id_fkey"
            columns: ["billing_entity_id"]
            isOneToOne: false
            referencedRelation: "billing_entities"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "users_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      vendor_items: {
        Row: {
          cost: number
          created_at: string
          deleted_at: string | null
          id: string
          is_preferred: boolean
          lead_time_days: number | null
          moq: number | null
          notes: string | null
          organization_id: string | null
          purchase_pack_qty: number
          purchase_uom: string
          sku_id: string
          updated_at: string
          vendor_id: string
          vendor_name: string
          vendor_sku: string | null
        }
        Insert: {
          cost?: number
          created_at: string
          deleted_at?: string | null
          id: string
          is_preferred?: boolean
          lead_time_days?: number | null
          moq?: number | null
          notes?: string | null
          organization_id?: string | null
          purchase_pack_qty?: number
          purchase_uom?: string
          sku_id: string
          updated_at: string
          vendor_id: string
          vendor_name?: string
          vendor_sku?: string | null
        }
        Update: {
          cost?: number
          created_at?: string
          deleted_at?: string | null
          id?: string
          is_preferred?: boolean
          lead_time_days?: number | null
          moq?: number | null
          notes?: string | null
          organization_id?: string | null
          purchase_pack_qty?: number
          purchase_uom?: string
          sku_id?: string
          updated_at?: string
          vendor_id?: string
          vendor_name?: string
          vendor_sku?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "vendor_items_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "vendor_items_sku_id_fkey"
            columns: ["sku_id"]
            isOneToOne: false
            referencedRelation: "skus"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "vendor_items_vendor_id_fkey"
            columns: ["vendor_id"]
            isOneToOne: false
            referencedRelation: "vendors"
            referencedColumns: ["id"]
          },
        ]
      }
      vendors: {
        Row: {
          address: string
          contact_name: string
          created_at: string
          deleted_at: string | null
          email: string
          id: string
          name: string
          organization_id: string | null
          phone: string
        }
        Insert: {
          address?: string
          contact_name?: string
          created_at: string
          deleted_at?: string | null
          email?: string
          id: string
          name: string
          organization_id?: string | null
          phone?: string
        }
        Update: {
          address?: string
          contact_name?: string
          created_at?: string
          deleted_at?: string | null
          email?: string
          id?: string
          name?: string
          organization_id?: string | null
          phone?: string
        }
        Relationships: [
          {
            foreignKeyName: "vendors_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      withdrawal_items: {
        Row: {
          amount: number
          cost: number
          cost_total: number
          id: string
          name: string
          quantity: number
          sell_cost: number
          sell_uom: string
          sku: string
          sku_id: string
          unit: string
          unit_price: number
          withdrawal_id: string
        }
        Insert: {
          amount?: number
          cost?: number
          cost_total?: number
          id: string
          name?: string
          quantity: number
          sell_cost?: number
          sell_uom?: string
          sku?: string
          sku_id: string
          unit?: string
          unit_price?: number
          withdrawal_id: string
        }
        Update: {
          amount?: number
          cost?: number
          cost_total?: number
          id?: string
          name?: string
          quantity?: number
          sell_cost?: number
          sell_uom?: string
          sku?: string
          sku_id?: string
          unit?: string
          unit_price?: number
          withdrawal_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "withdrawal_items_withdrawal_id_fkey"
            columns: ["withdrawal_id"]
            isOneToOne: false
            referencedRelation: "withdrawals"
            referencedColumns: ["id"]
          },
        ]
      }
      withdrawals: {
        Row: {
          billing_entity: string
          billing_entity_id: string | null
          contractor_company: string
          contractor_id: string
          contractor_name: string
          cost_total: number
          created_at: string
          id: string
          invoice_id: string | null
          items: string | null
          job_id: string
          notes: string | null
          organization_id: string | null
          paid_at: string | null
          payment_status: string
          processed_by_id: string
          processed_by_name: string
          service_address: string
          subtotal: number
          tax: number
          tax_rate: number
          total: number
        }
        Insert: {
          billing_entity?: string
          billing_entity_id?: string | null
          contractor_company?: string
          contractor_id: string
          contractor_name?: string
          cost_total: number
          created_at: string
          id: string
          invoice_id?: string | null
          items?: string | null
          job_id: string
          notes?: string | null
          organization_id?: string | null
          paid_at?: string | null
          payment_status?: string
          processed_by_id: string
          processed_by_name?: string
          service_address: string
          subtotal: number
          tax: number
          tax_rate?: number
          total: number
        }
        Update: {
          billing_entity?: string
          billing_entity_id?: string | null
          contractor_company?: string
          contractor_id?: string
          contractor_name?: string
          cost_total?: number
          created_at?: string
          id?: string
          invoice_id?: string | null
          items?: string | null
          job_id?: string
          notes?: string | null
          organization_id?: string | null
          paid_at?: string | null
          payment_status?: string
          processed_by_id?: string
          processed_by_name?: string
          service_address?: string
          subtotal?: number
          tax?: number
          tax_rate?: number
          total?: number
        }
        Relationships: [
          {
            foreignKeyName: "withdrawals_billing_entity_id_fkey"
            columns: ["billing_entity_id"]
            isOneToOne: false
            referencedRelation: "billing_entities"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "withdrawals_contractor_id_fkey"
            columns: ["contractor_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "withdrawals_invoice_id_fkey"
            columns: ["invoice_id"]
            isOneToOne: false
            referencedRelation: "invoices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "withdrawals_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "withdrawals_processed_by_id_fkey"
            columns: ["processed_by_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      entity_edges: {
        Row: {
          org_id: string | null
          relation: string | null
          source_id: string | null
          source_type: string | null
          target_id: string | null
          target_type: string | null
        }
        Relationships: []
      }
    }
    Functions: {
      jwt_organization_id: { Args: never; Returns: string }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {},
  },
} as const

