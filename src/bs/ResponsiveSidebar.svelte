<script lang="ts">
 import {onMount} from 'svelte';
 import {t} from '../lib/i18n';

 export let enabled=false;
 export let narrow=false;
 export let opened=false;
 export let portalTarget:HTMLDialogElement|undefined=undefined;
 export let onDismiss:()=>void=()=>{};

 onMount(()=>{
  if(!enabled)return;
  const query=window.matchMedia('(width < 960px)');
  const sync=(matches:boolean)=>{
   if(!matches){if(portalTarget?.open)portalTarget.close();opened=false;}
   narrow=matches;
  };
  const changed=(event:MediaQueryListEvent)=>sync(event.matches);
  sync(query.matches);
  query.addEventListener('change',changed);
  return()=>{query.removeEventListener('change',changed);if(portalTarget?.open)portalTarget.close();};
 });

 $:if(enabled&&narrow&&portalTarget){
  if(opened&&!portalTarget.open)portalTarget.showModal();
  else if(!opened&&portalTarget.open)portalTarget.close();
 }

 function backdropClick(event:MouseEvent){if(event.target===portalTarget)onDismiss();}
</script>

{#if enabled&&narrow}
 <dialog class="navigation-sheet" aria-label={$t('文件夹管理')} bind:this={portalTarget} on:cancel|preventDefault={onDismiss} on:click={backdropClick}>
  <slot/>
 </dialog>
{:else}
 <slot/>
{/if}
