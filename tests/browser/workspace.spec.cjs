const {test,expect}=require('@playwright/test');

test('review artifact and memory, then inspect durable output',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Run task'}).click();
  await expect(page.getByRole('heading',{name:'Save this artifact?'})).toBeVisible();
  await expect(page.locator('#artifacts')).toContainText('Approved outputs will appear here.');
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:'docs/workspace.png'});
  await page.getByRole('button',{name:'Approve & continue'}).click();
  await expect(page.getByRole('heading',{name:'Remember this for future tasks?'})).toBeVisible();
  await expect(page.locator('#artifacts')).toContainText('Release brief');
  await page.getByRole('button',{name:'Approve & continue'}).click();
  await expect(page.locator('#task-metrics')).toContainText('succeeded');
  await expect(page.locator('#task-metrics')).toContainText('5 / 10');
  await page.getByRole('button',{name:/Memory/}).first().click();
  await expect(page.locator('#memories')).toContainText('Mina');
  await page.reload();
  await expect(page.locator('#artifacts')).toContainText('Release brief');
  await page.setViewportSize({width:390,height:844});
  await page.evaluate(()=>window.scrollTo(0,0));
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'docs/workspace-mobile.png',fullPage:true});
  expect(errors).toEqual([]);
});

test('rejecting a write does not save an artifact',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Run task'}).click();
  await expect(page.getByRole('heading',{name:'Save this artifact?'})).toBeVisible();
  await page.getByRole('button',{name:'Reject',exact:true}).click();
  await expect(page.locator('#task-metrics')).toContainText('succeeded');
  await expect(page.locator('#artifact-count')).toHaveText('0 saved');
  await expect(page.locator('#result')).toContainText('denied action');
});

test('document content is rendered as text',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:/Documents/}).first().click();
  await page.getByRole('button',{name:'Add document'}).click();
  await page.getByLabel('Title',{exact:true}).fill('Browser check');
  await page.getByLabel('Content',{exact:true}).fill('<script>window.injected=true</script>');
  await page.getByRole('button',{name:'Save document'}).click();
  await expect(page.locator('#document-dialog')).not.toBeVisible();
  await expect(page.locator('#documents')).toContainText('<script>window.injected=true</script>');
  expect(await page.evaluate(()=>window.injected)).toBeUndefined();
});
